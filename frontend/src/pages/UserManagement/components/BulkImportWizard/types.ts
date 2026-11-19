import { IRowValidation } from '../../../../utils/studentImportValidator';

export interface IBulkRowError {
    row: number;
    name?: string;
    email?: string;
    error: string;
}

export interface IBulkRowSuccess {
    row: number;
    name?: string;
    email?: string;
    roll_no?: string;
}

export interface IBulkResult {
    total: number;
    successful: number;
    failed: number;
    errors?: IBulkRowError[];
    created_students?: IBulkRowSuccess[];
}

export interface ILocalClass {
    id: string | number;
    class_name?: string;
    name?: string;
}

export interface IBulkWizardState {
    file: File | null;
    rows: Record<string, any>[];
    validations: IRowValidation[];
    classId: string;
    sectionId: string;
    defaultPassword: string;
    result: IBulkResult | null;
}

export const STEPS = ['Upload', 'Validate', 'Confirm', 'Result'] as const;
export type StepIndex = 0 | 1 | 2 | 3;
