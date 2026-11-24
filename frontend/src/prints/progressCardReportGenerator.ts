/**
 * Progress Card PDF Generator
 * Generates individual student progress report card for a specific exam.
 * Portrait A4, reuses shared header, footer, signature, and styles.
 */

import pdfMake from 'pdfmake/build/pdfmake';
import {
    getReportHeader,
    getReportFooter,
    getSignatureSection,
    commonPdfStyles,
    loadPdfFonts,
} from './HeaderAndFooterComponent';
import type { InstitutionData, PdfAction } from './printTypes';
import type { IProgressCard } from '../types/index';
import { formatDateRange } from '../utils/dateRange';

/**
 * Grade color helper
 */
const gradeColor = (grade: string): string => {
    if (grade === 'A+' || grade === 'A') return '#4caf50';
    if (grade === 'F') return '#f44336';
    return '#ff9800';
};

/**
 * One student's report card content (used for a single card and for a whole class in one PDF).
 */
const buildProgressCardContent = (
    data: IProgressCard,
    institutionData: InstitutionData
): { content: unknown[]; title: string; subtitle: string } => {
    const {
        student_name,
        roll_number,
        class_name,
        section_name,
        exam_name,
        subject_details,
        overall_total_marks,
        overall_max_marks,
        overall_percentage,
        overall_grade,
        result,
        rank,
        total_students,
        class_teacher_name,
        class_teacher_remarks,
        attendance,
    } = data;

    const title = 'STUDENT PROGRESS REPORT CARD';
    const subtitle = `${exam_name} | Class: ${class_name} - ${section_name}`;

    // ─── Student Information ───
    const studentInfoSection: any = {
        style: 'section',
        table: {
            widths: ['25%', '25%', '25%', '25%'],
            body: [
                [
                    { text: 'Student Information', fontSize: 11, bold: true, colSpan: 4, fillColor: '#667eea', color: '#ffffff', margin: [5, 4, 5, 4] },
                    {}, {}, {},
                ],
                [
                    { text: 'Student Name', bold: true, fillColor: '#f5f5f5', fontSize: 9 },
                    { text: student_name, colSpan: 3, fontSize: 9 },
                    {}, {},
                ],
                [
                    { text: 'Roll Number', bold: true, fillColor: '#f5f5f5', fontSize: 9 },
                    { text: roll_number, fontSize: 9 },
                    { text: 'Class & Section', bold: true, fillColor: '#f5f5f5', fontSize: 9 },
                    { text: `${class_name} - ${section_name}`, fontSize: 9 },
                ],
                [
                    { text: 'Examination', bold: true, fillColor: '#f5f5f5', fontSize: 9 },
                    { text: exam_name, colSpan: 3, fontSize: 9 },
                    {}, {},
                ],
            ],
        },
        layout: {
            hLineWidth: () => 0.5,
            vLineWidth: () => 0.5,
            hLineColor: () => '#e0e0e0',
            vLineColor: () => '#e0e0e0',
        },
        margin: [0, 0, 0, 15],
    };

    // ─── Subject Marks Table ───
    const hasInternalExternal = subject_details.some((s) => s.has_internal_external);

    // Header
    const marksHeader: any[] = [
        { text: '#', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' },
        { text: 'Subject', style: 'tableHeader', fillColor: '#667eea', color: '#ffffff' },
    ];

    if (hasInternalExternal) {
        marksHeader.push(
            { text: 'Internal', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' },
            { text: 'External', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' }
        );
    }

    marksHeader.push(
        { text: 'Total', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' },
        { text: 'Max', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' },
        { text: 'Grade', style: 'tableHeader', alignment: 'center', fillColor: '#667eea', color: '#ffffff' },
        { text: 'Remarks', style: 'tableHeader', fillColor: '#667eea', color: '#ffffff' }
    );

    const marksBody: any[][] = [marksHeader];

    // Subject rows
    subject_details.forEach((subj, index) => {
        const row: any[] = [
            { text: index + 1, alignment: 'center', fontSize: 9 },
            {
                stack: [
                    { text: subj.subject_name, fontSize: 10, bold: true },
                    { text: `(${subj.subject_code})`, fontSize: 8, color: '#666666', margin: [0, 2, 0, 0] },
                ],
            },
        ];

        if (hasInternalExternal) {
            if (subj.has_internal_external) {
                row.push(
                    { text: subj.is_absent || subj.internal_marks === null ? '-' : subj.internal_marks, alignment: 'center', fontSize: 10 },
                    { text: subj.is_absent || subj.external_marks === null ? '-' : subj.external_marks, alignment: 'center', fontSize: 10 }
                );
            } else {
                row.push(
                    { text: '-', alignment: 'center', color: '#cccccc', fontSize: 10 },
                    { text: '-', alignment: 'center', color: '#cccccc', fontSize: 10 }
                );
            }
        }

        row.push(
            {
                // AB = absent, "-" = marks not entered yet; red when below the subject's pass mark
                text: subj.is_absent ? 'AB' : subj.total_marks === null ? '-' : subj.total_marks,
                alignment: 'center',
                fontSize: 10,
                bold: true,
                color: subj.is_absent || subj.passed === false ? '#f44336' : '#333333',
            },
            { text: subj.max_marks, alignment: 'center', fontSize: 10 },
            {
                text: subj.is_absent || subj.total_marks === null ? '-' : subj.grade,
                alignment: 'center',
                fontSize: 10,
                bold: true,
                color: subj.is_absent || subj.total_marks === null ? '#cccccc' : gradeColor(subj.grade),
            },
            { text: subj.remarks || '-', fontSize: 8, color: '#666666' }
        );

        marksBody.push(row);
    });

    // Grand total row
    const totalRow: any[] = [
        { text: '', border: [false, false, false, false] },
        { text: 'GRAND TOTAL', bold: true, fontSize: 11, fillColor: '#f5f5f5' },
    ];

    if (hasInternalExternal) {
        totalRow.push({ text: '', fillColor: '#f5f5f5' }, { text: '', fillColor: '#f5f5f5' });
    }

    totalRow.push(
        { text: overall_total_marks, alignment: 'center', fontSize: 11, bold: true, fillColor: '#f5f5f5' },
        { text: overall_max_marks, alignment: 'center', fontSize: 11, bold: true, fillColor: '#f5f5f5' },
        { text: overall_grade, alignment: 'center', fontSize: 11, bold: true, fillColor: '#f5f5f5', color: '#667eea' },
        { text: '', fillColor: '#f5f5f5' }
    );

    marksBody.push(totalRow);

    const marksTable: any = {
        style: 'section',
        table: {
            headerRows: 1,
            widths: hasInternalExternal
                ? [20, '*', 45, 45, 45, 40, 40, 80]
                : [20, '*', 45, 40, 40, 80],
            body: marksBody,
        },
        layout: {
            hLineWidth: (i: number, node: any) =>
                i === 0 || i === 1 || i === node.table.body.length ? 1 : 0.5,
            vLineWidth: () => 0.5,
            hLineColor: (i: number) => (i === 0 || i === 1 ? '#667eea' : '#e0e0e0'),
            vLineColor: () => '#e0e0e0',
        },
        margin: [0, 0, 0, 15],
    };

    // ─── Performance Summary ───
    const performanceSummary: any = {
        style: 'section',
        table: {
            widths: result ? ['*', '*', '*', '*'] : ['*', '*', '*'],
            body: [
                [
                    ...(result ? [{
                        stack: [
                            { text: 'Result', fontSize: 9, color: '#666666', alignment: 'center' },
                            {
                                text: result === 'Incomplete' ? 'Incomplete (marks pending)' : result,
                                fontSize: result === 'Incomplete' ? 11 : 16,
                                bold: true,
                                color: result === 'Pass' ? '#2e7d32' : result === 'Fail' ? '#c62828' : '#757575',
                                alignment: 'center',
                                margin: [0, 5, 0, 0],
                            },
                        ],
                        fillColor: '#f5f5f5',
                        margin: [10, 10, 10, 10],
                    }] : []),
                    {
                        stack: [
                            { text: 'Overall Percentage', fontSize: 9, color: '#666666', alignment: 'center' },
                            { text: `${overall_percentage.toFixed(2)}%`, fontSize: 16, bold: true, color: '#1976d2', alignment: 'center', margin: [0, 5, 0, 0] },
                        ],
                        fillColor: '#e3f2fd',
                        margin: [10, 10, 10, 10],
                    },
                    {
                        stack: [
                            { text: 'Overall Grade', fontSize: 9, color: '#666666', alignment: 'center' },
                            { text: overall_grade, fontSize: 16, bold: true, color: '#4caf50', alignment: 'center', margin: [0, 5, 0, 0] },
                        ],
                        fillColor: '#e8f5e9',
                        margin: [10, 10, 10, 10],
                    },
                    {
                        stack: [
                            { text: 'Class Rank', fontSize: 9, color: '#666666', alignment: 'center' },
                            { text: `${rank} / ${total_students}`, fontSize: 16, bold: true, color: '#ff9800', alignment: 'center', margin: [0, 5, 0, 0] },
                        ],
                        fillColor: '#fff3e0',
                        margin: [10, 10, 10, 10],
                    },
                ],
            ],
        },
        layout: 'noBorders',
        margin: [0, 0, 0, 15],
    };

    // ─── Attendance ───
    const attendanceSection: any = attendance
        ? {
            style: 'section',
            table: {
                widths: ['*'],
                body: [
                    [
                        {
                            stack: [
                                { text: 'Attendance', bold: true, fontSize: 10, margin: [0, 0, 0, 5] },
                                {
                                    text: `Days Present: ${attendance.present_days} / ${attendance.total_days} (${attendance.percentage.toFixed(1)}%)${formatDateRange(attendance.from, attendance.to) ? ` — ${formatDateRange(attendance.from, attendance.to)}` : ''}`,
                                    fontSize: 9,
                                },
                            ],
                            fillColor: '#f5f5f5',
                            margin: [10, 10, 10, 10],
                        },
                    ],
                ],
            },
            layout: {
                hLineWidth: () => 0.5,
                vLineWidth: () => 0.5,
                hLineColor: () => '#e0e0e0',
                vLineColor: () => '#e0e0e0',
            },
            margin: [0, 0, 0, 10],
        }
        : null;

    // ─── Remarks ───
    const remarksSection: any = {
        style: 'section',
        table: {
            widths: ['*'],
            body: [
                [
                    {
                        stack: [
                            { text: "Class Teacher's Remarks", bold: true, fontSize: 10, margin: [0, 0, 0, 5] },
                            { text: class_teacher_remarks || 'No remarks provided.', fontSize: 9 },
                        ],
                        fillColor: '#e3f2fd',
                        margin: [10, 10, 10, 10],
                    },
                ],
            ],
        },
        layout: {
            hLineWidth: () => 0.5,
            vLineWidth: () => 0.5,
            hLineColor: () => '#e0e0e0',
            vLineColor: () => '#e0e0e0',
        },
        margin: [0, 0, 0, 15],
    };

    // ─── Grading Scale ───
    const gradingScale = {
        text: [
            { text: 'Grading Scale: ', bold: true, fontSize: 8 },
            { text: 'A+ (90-100)  |  A (80-89)  |  B+ (70-79)  |  B (60-69)  |  C (50-59)  |  D (35-49)  |  F (Below 35)', fontSize: 7, color: '#666666' },
        ],
        margin: [0, 0, 0, 10],
    };

    // ─── Note ───
    const noteSection = {
        text: [
            { text: 'Note: ', bold: true, fontSize: 8 },
            { text: 'This is a computer-generated document.', fontSize: 7, italics: true, color: '#666666' },
        ],
        margin: [0, 5, 0, 0],
    };

    // ─── Content ───
    const content: any[] = [
        getReportHeader(institutionData, title, subtitle, 'portrait', true),
        studentInfoSection,
        marksTable,
        performanceSummary,
        ...(attendanceSection ? [attendanceSection] : []),
        remarksSection,
        gradingScale,
        noteSection,
        getSignatureSection([
            { label: `Class Teacher${class_teacher_name ? '\n' + class_teacher_name : ''}`, position: 'left' },
            { label: 'Parent / Guardian', position: 'center' },
            { label: 'Principal', position: 'right' },
        ]),
    ];

    return { content, title, subtitle };
};

/**
 * Generate Progress Card PDF
 */
export const generateProgressCardPdf = async (
    data: IProgressCard,
    institutionData: InstitutionData,
    action: PdfAction = 'download'
): Promise<void> => {
    await loadPdfFonts();
    const { content, title, subtitle } = buildProgressCardContent(data, institutionData);
    const { student_name, exam_name } = data;

    // ─── Document Definition ───
    const docDefinition: any = {
        pageSize: 'A4',
        pageOrientation: 'portrait',
        pageMargins: [30, 20, 30, 50],
        header: (currentPage: number, _pageCount: number) => {
            if (currentPage === 1) return null;
            return {
                stack: [
                    {
                        text: title,
                        alignment: 'center',
                        fontSize: 10,
                        bold: true,
                        color: '#667eea',
                        margin: [30, 2, 30, 1],
                    },
                    {
                        text: subtitle,
                        alignment: 'center',
                        fontSize: 8,
                        color: '#666666',
                        margin: [30, 0, 30, 0],
                    },
                ],
            };
        },
        footer: (currentPage: number, pageCount: number) => {
            return getReportFooter(currentPage, pageCount, institutionData?.generatedBy);
        },
        content,
        styles: commonPdfStyles,
        defaultStyle: {
            fontSize: 9,
            color: '#333333',
        },
    };

    // ─── Output ───
    if (action === 'print') {
        pdfMake.createPdf(docDefinition).print();
    } else if (action === 'download') {
        const filename = `Progress_Card_${student_name.replace(/\s+/g, '_')}_${exam_name.replace(/\s+/g, '_')}.pdf`;
        pdfMake.createPdf(docDefinition).download(filename);
    } else {
        pdfMake.createPdf(docDefinition).open();
    }
};

/**
 * Every student's report card in one PDF, each starting on a new page.
 */
export const generateProgressCardsPdf = async (
    cards: IProgressCard[],
    institutionData: InstitutionData,
    action: PdfAction = 'download',
    fileLabel = 'Class'
): Promise<void> => {
    if (!cards.length) return;
    await loadPdfFonts();
    const content: unknown[] = [];
    cards.forEach((card, index) => {
        const built = buildProgressCardContent(card, institutionData);
        content.push({ stack: built.content, ...(index > 0 ? { pageBreak: 'before' } : {}) });
    });
    const docDefinition = {
        pageSize: 'A4',
        pageOrientation: 'portrait',
        pageMargins: [30, 20, 30, 50],
        footer: (currentPage: number, pageCount: number) => getReportFooter(currentPage, pageCount, institutionData?.generatedBy),
        content,
        styles: commonPdfStyles,
        defaultStyle: { fontSize: 9, color: '#333333' },
    };
    const pdf = pdfMake.createPdf(docDefinition as unknown as Parameters<typeof pdfMake.createPdf>[0]);
    if (action === 'print') {
        pdf.print();
    } else if (action === 'download') {
        const exam = (cards[0].exam_name || 'Exam').replace(/\s+/g, '_');
        pdf.download(`Report_Cards_${fileLabel.replace(/\s+/g, '_')}_${exam}.pdf`);
    } else {
        pdf.open();
    }
};
