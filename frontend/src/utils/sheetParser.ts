/**
 * Universal sheet parser — accepts .csv, .xls, .xlsx via SheetJS.
 * Returns trimmed string values keyed by trimmed header names.
 */
import * as XLSX from 'xlsx';

export type SheetRow = Record<string, string>;

export async function parseSheet(file: File): Promise<SheetRow[]> {
    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer, { type: 'array', cellDates: true });
    if (!wb.SheetNames.length) return [];
    const sheet = wb.Sheets[wb.SheetNames[0]];
    const json: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false });

    return json.map((r) =>
        Object.fromEntries(
            Object.entries(r).map(([k, v]) => [
                String(k).trim(),
                String(v ?? '').trim(),
            ])
        )
    );
}

/**
 * Build a downloadable XLSX blob from headers + rows.
 */
export function buildXlsx(headers: string[], rows: string[][]): Blob {
    const aoa = [headers, ...rows];
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Students');
    const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    return new Blob([buf], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
}

/**
 * Trigger a file download from a Blob.
 */
export function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
