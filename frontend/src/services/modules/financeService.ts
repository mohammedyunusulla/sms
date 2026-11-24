/**
 * Finance Service
 * Handles all API calls for Finance Management:
 * - Fee Structure (create, list, assign, delete)
 * - Fee Collection (search student, summary, payments, installments)
 * - Expenses (CRUD with category/date filters)
 * - Salary Setup (CRUD for staff salary structures)
 * - Salary Payments (generate, mark paid/unpaid)
 */

import { getApiClient, getInstitutionId } from '../api/client';
import type { ICollectionReport, IDefaultersReport } from '../../types/index';

class FinanceService {

    // ============================================
    // Fee Structure
    // ============================================

    async listFeeStructures(academicYearId: string | number): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/fee/structure/list/${skid}`, {
            params: { academic_year_id: academicYearId },
        });
        return response;
    }

    async createFeeStructure(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/structure/create/${skid}`, data);
        return response;
    }

    async updateFeeStructure(feeId: number | string, data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.put(`/fee/structure/update/${skid}/${feeId}`, data);
        return response;
    }

    async deleteFeeStructure(feeId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.delete(`/fee/structure/delete/${skid}/${feeId}`);
        return response;
    }

    async deleteClassFeeStructures(classId: number | string, academicYearId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.delete(`/fee/structure/delete-class/${skid}/${classId}/${academicYearId}`);
        return response;
    }

    async assignFeesToClass(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/assign/class/${skid}`, data);
        return response;
    }

    // ============================================
    // Fee Collection
    // ============================================

    async searchStudent(query: string, academicYearId: string | number): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/fee/search-student/${skid}`, {
            params: { q: query, academic_year_id: academicYearId },
        });
        return Array.isArray(response) ? response : (response as any).data || [];
    }

    async getStudentFeeSummary(userId: number | string, academicYearId: string | number): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/fee/summary/student/${skid}/${userId}`, {
            params: { academic_year_id: academicYearId },
        });
        return response;
    }

    async getInstallments(feeId: number | string): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/fee/installments/get/${skid}/${feeId}`);
        return response?.data || [];
    }

    async recordPayment(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/payment/record/${skid}`, data);
        return response;
    }

    async recordInstallmentPayment(installmentId: number | string, data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/installments/payment/${skid}/${installmentId}`, data);
        return response;
    }

    async convertToFullPayment(feeId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/payment/convert-to-full/${skid}/${feeId}`);
        return response;
    }

    async autoGenerateInstallments(data: { student_fee_id: number | string; preview?: boolean }): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/installments/auto-generate-recurring/${skid}`, data);
        return response;
    }

    /** The server's recurring plan for a fee (what Generate would create), without saving it. */
    async previewRecurringInstallments(studentFeeId: number | string): Promise<{ installment_name: string; amount: number; due_date: string }[]> {
        const result: any = await this.autoGenerateInstallments({ student_fee_id: studentFeeId, preview: true });
        return result?.data || [];
    }

    async createManualInstallments(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/fee/installments/create/${skid}`, data);
        return response;
    }

    // ============================================
    // Classes (for fee structure form)
    // ============================================

    async listClasses(): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/classes/list/${skid}`);
        // The API returns { code, data: [...] }; accept a bare array too.
        return Array.isArray(response) ? response : (response as any)?.data || [];
    }

    // ============================================
    // Expenses
    // ============================================

    async listExpenses(params: {
        academic_year_id: string | number;
        category?: string;
        start_date?: string;
        end_date?: string;
    }): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/expenses/${skid}`, { params });
        return Array.isArray(response) ? response : (response as any).expenses || [];
    }

    async createExpense(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/expenses/create/${skid}`, data);
        return response;
    }

    async updateExpense(expenseId: number | string, data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.put(`/expenses/update/${skid}/${expenseId}`, data);
        return response;
    }

    async deleteExpense(expenseId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.delete(`/expenses/delete/${skid}/${expenseId}`);
        return response;
    }

    // ============================================
    // Salary Setup
    // ============================================

    async listSalarySetups(academicYearId: string | number): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/expenses/list/salary-setup/${skid}`, {
            params: { academic_year_id: academicYearId },
        });
        return Array.isArray(response) ? response : (response as any).salary_setups || [];
    }

    async createSalarySetup(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/expenses/salary-setup/${skid}`, data);
        return response;
    }

    async updateSalarySetup(data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.put(`/expenses/salary-setup/update/${skid}`, data);
        return response;
    }

    async deleteSalarySetup(setupId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.delete(`/expenses/salary-setup/delete/${skid}/${setupId}`);
        return response;
    }

    async listStaff(): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/users/list/staff/${skid}`);
        return Array.isArray(response) ? response : (response as any).staff || [];
    }

    // ============================================
    // Salary Payments
    // ============================================

    async listSalaryPayments(academicYearId: string | number): Promise<any[]> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.get(`/expenses/salary-payments/${skid}`, {
            params: { academic_year_id: academicYearId },
        });
        return Array.isArray(response) ? response : (response as any).salary_payments || [];
    }

    async generateSalaryPayments(data: { month: number; year: number; academic_year_id: string | number }): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.post(`/expenses/salary-payments/generate/${skid}`, data);
        return response;
    }

    async markSalaryPaid(paymentId: number | string, data: any): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.put(`/expenses/salary-payments/${paymentId}/mark-paid/${skid}`, data);
        return response;
    }

    async markSalaryUnpaid(paymentId: number | string): Promise<any> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = await api.put(`/expenses/salary-payments/${skid}/mark-unpaid/${paymentId}`);
        return response;
    }

    // ============================================
    // Cancel payment / discounts / defaulters
    // ============================================

    async cancelPayment(paymentId: number | string, reason: string): Promise<unknown> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        return api.post(`/fee/payment/cancel/${skid}/${paymentId}`, { reason });
    }

    async applyDiscount(data: {
        student_id: number;
        academic_year_id: number | string;
        discount_name: string;
        discount_type: 'PERCENTAGE' | 'FIXED';
        discount_value: number;
        student_fee_ids: number[];
        reason?: string;
    }): Promise<{ data?: { total_discount_added?: number } }> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        return api.post(`/fee/discount/apply/${skid}`, data);
    }

    async getCollectionReport(params: { start_date: string; end_date: string; class_id?: string | number }): Promise<ICollectionReport> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const query: Record<string, string> = { start_date: params.start_date, end_date: params.end_date };
        if (params.class_id) query.class_id = String(params.class_id);
        const response = (await api.get(`/fee/report/collection/${skid}`, { params: query })) as unknown as { data?: ICollectionReport };
        return response?.data || { total_collected: 0, total_transactions: 0, collection_by_mode: {}, payments: [] };
    }

    async getDefaulters(academicYearId: number | string, asOfDate?: string): Promise<IDefaultersReport> {
        const api = getApiClient();
        const skid = getInstitutionId();
        if (!skid) throw new Error('Institution ID not found. Please log in again.');
        const response = (await api.get(`/fee/report/defaulters/${skid}`, {
            params: { academic_year_id: academicYearId, ...(asOfDate ? { as_of_date: asOfDate } : {}) },
        })) as unknown as { data?: IDefaultersReport } & IDefaultersReport;
        return response?.data || response;
    }
}

export const financeService = new FinanceService();
