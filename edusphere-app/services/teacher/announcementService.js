import api from "../../lib/axios";

const announcementService = {
    async getAnnouncements(skid, { academicYearId, userRole, institutionUserId, limit, announcementType, priority } = {}) {
        const params = {
            academic_year_id: academicYearId,
            user_role: userRole,
            institution_user_id: institutionUserId,
        };
        if (limit) params.limit = limit;
        if (announcementType) params.announcement_type = announcementType;
        if (priority) params.priority = priority;

        return api.get(`/announcements/list/${skid}`, { params });
    },
};

export default announcementService;
