/**
 * usePageSearch Hook
 * Custom hook for searching pages with fuzzy matching and role-based filtering
 */

import { useMemo } from 'react';
import { searchablePages, SearchablePage } from '../data/searchablePages';
import { UserRole } from '../types/common';
import { ROUTE_PERMISSION_MAP } from '../config/permissions';

interface UsePageSearchOptions {
    query: string;
    userRole: UserRole | null;
    /** usePermissions().canOpen - the same rule as the menu */
    canOpen: (path: string) => boolean;
}

interface GroupedResults {
    category: string;
    pages: SearchablePage[];
}

export const usePageSearch = ({ query, userRole, canOpen }: UsePageSearchOptions) => {
    const results = useMemo(() => {
        // If no query, return empty results
        if (!query.trim()) {
            return [];
        }

        const searchTerm = query.toLowerCase().trim();

        // Filter pages based on user role and search query
        const filteredPages = searchablePages.filter((page) => {
            // Check if user has access to this page
            // A page guarded by a permission follows the role's ticks (custom roles, Principal); the rest
            // (dashboard, profile) keep their role list. It used to be the role list only (QA A31).
            if (!userRole || !canOpen(page.route)) {
                return false;
            }
            const guard = ROUTE_PERMISSION_MAP[page.route];
            const tickDecided = !!guard && (!!guard.permission || !!guard.anyPermission?.length || !!guard.superAdminOnly);
            if (!tickDecided && !page.roles.includes(userRole)) {
                return false;
            }

            // Search in name, description, and keywords
            const nameMatch = page.name.toLowerCase().includes(searchTerm);
            const descriptionMatch = page.description.toLowerCase().includes(searchTerm);
            const keywordMatch = page.keywords.some((keyword) =>
                keyword.toLowerCase().includes(searchTerm)
            );
            const categoryMatch = page.category.toLowerCase().includes(searchTerm);

            return nameMatch || descriptionMatch || keywordMatch || categoryMatch;
        });

        // Group results by category
        const grouped: GroupedResults[] = [];
        const categoryMap = new Map<string, SearchablePage[]>();

        filteredPages.forEach((page) => {
            const existing = categoryMap.get(page.category) || [];
            existing.push(page);
            categoryMap.set(page.category, existing);
        });

        categoryMap.forEach((pages, category) => {
            grouped.push({ category, pages });
        });

        return grouped;
    }, [query, userRole, canOpen]);

    const totalResults = useMemo(() => {
        return results.reduce((acc, group) => acc + group.pages.length, 0);
    }, [results]);

    const hasResults = totalResults > 0;

    return {
        results,
        totalResults,
        hasResults,
    };
};
