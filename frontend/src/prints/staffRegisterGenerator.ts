/**
 * Monthly staff attendance register (A4 landscape): one row per staff member, one column per day, then totals.
 */
import pdfMake from 'pdfmake/build/pdfmake';
import { getReportHeader, getReportFooter, getSignatureSection, commonPdfStyles, loadPdfFonts } from './HeaderAndFooterComponent';
import type { TDocumentDefinitions } from 'pdfmake/interfaces';
import type { InstitutionData, PdfAction } from './printTypes';

export interface StaffRegisterPdfData {
    monthLabel: string;
    days: number;
    rows: { name: string; role: string; days: Record<string, string>; totals: Record<string, number> }[];
}

const CODE: Record<string, { text: string; color: string }> = {
    PRESENT: { text: 'P', color: '#2e7d32' },
    ABSENT: { text: 'A', color: '#c62828' },
    LATE: { text: 'L', color: '#ef6c00' },
    HALF_DAY: { text: 'H', color: '#e65100' },
    LEAVE: { text: 'LV', color: '#1565c0' },
    UNPAID_LEAVE: { text: 'UL', color: '#6a1b9a' },
    HOLIDAY: { text: 'HO', color: '#8e24aa' },
    WEEKLY_OFF: { text: 'WO', color: '#9e9e9e' },
};
const TOTALS = [['PRESENT', 'P'], ['ABSENT', 'A'], ['LATE', 'L'], ['HALF_DAY', 'H'], ['LEAVE', 'LV'], ['UNPAID_LEAVE', 'UL'], ['NOT_MARKED', 'NM']];

export const generateStaffRegisterPdf = async (
    data: StaffRegisterPdfData,
    institutionData: InstitutionData,
    action: PdfAction = 'download',
): Promise<void> => {
    await loadPdfFonts();
    const title = 'STAFF ATTENDANCE REGISTER';
    const subtitle = data.monthLabel;
    const head = { fillColor: '#667eea', color: '#ffffff', bold: true, fontSize: 6.5, alignment: 'center' as const };
    const dayNums = Array.from({ length: data.days }, (_, i) => String(i + 1));

    const body: unknown[][] = [[
        { text: 'Staff', ...head, alignment: 'left' },
        ...dayNums.map((d) => ({ text: d, ...head })),
        ...TOTALS.map(([, label]) => ({ text: label, ...head, fillColor: '#4a5bc4' })),
    ]];
    data.rows.forEach((r) => {
        body.push([
            { stack: [{ text: r.name, bold: true, fontSize: 7 }, { text: r.role, fontSize: 5.5, color: '#666666' }] },
            ...dayNums.map((d) => {
                const c = CODE[r.days[d]];
                return { text: c ? c.text : '', color: c?.color, fontSize: 6, bold: true, alignment: 'center' };
            }),
            ...TOTALS.map(([key]) => ({ text: String(r.totals[key] ?? 0), fontSize: 6.5, bold: true, alignment: 'center', fillColor: '#f5f5f5' })),
        ]);
    });

    const content: unknown[] = [
        getReportHeader(institutionData, title, subtitle, 'landscape', true),
        {
            table: { headerRows: 1, widths: [95, ...dayNums.map(() => '*'), ...TOTALS.map(() => 16)], body },
            layout: {
                hLineWidth: () => 0.5, vLineWidth: () => 0.5,
                hLineColor: () => '#dddddd', vLineColor: () => '#dddddd',
                paddingLeft: () => 1.5, paddingRight: () => 1.5, paddingTop: () => 2, paddingBottom: () => 2,
            },
        },
        {
            text: 'P Present · A Absent · L Late · H Half day · LV Leave · UL Unpaid leave (beyond the yearly balance; included in LV) · HO Holiday · WO Weekly off · NM Not marked (working days up to today with no entry)',
            fontSize: 7, italics: true, color: '#666666', margin: [0, 8, 0, 0],
        },
        getSignatureSection([{ label: 'Prepared by', position: 'left' }, { label: 'Principal Signature', position: 'right' }]),
    ];

    const docDefinition = {
        pageSize: 'A4',
        pageOrientation: 'landscape',
        pageMargins: [24, 40, 24, 50],
        footer: (currentPage: number, pageCount: number) => getReportFooter(currentPage, pageCount, institutionData?.generatedBy),
        content,
        styles: commonPdfStyles,
        defaultStyle: { fontSize: 8, color: '#333333' },
    };
    // the shared header/footer helpers are untyped, so the definition is checked by pdfmake at run time
    const doc = pdfMake.createPdf(docDefinition as unknown as TDocumentDefinitions);
    if (action === 'print') doc.print();
    else if (action === 'download') doc.download(`Staff_Attendance_${data.monthLabel.replace(/\s+/g, '_')}.pdf`);
    else doc.open();
};
