/**
 * Dashboard strip for holiday managers: a tentative holiday in the next 3 days still needs confirming or moving.
 */
import { FC, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Holiday, holidayService } from '../../services/modules/holidayService';
import { formatRange } from '../LeaveManagement/leaveDates';

const TentativeHolidayBanner: FC = () => {
    const [items, setItems] = useState<Holiday[]>([]);

    useEffect(() => {
        let alive = true;
        holidayService.tentativeSoon().then((h) => alive && setItems(h)).catch(() => undefined);
        return () => {
            alive = false;
        };
    }, []);

    if (!items.length) return null;
    const first = items[0];
    return (
        <Link to="/calendar"
            className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200 dark:hover:bg-amber-900/30">
            <span>
                <strong>{first.name}</strong> ({formatRange(first.start_date, first.end_date)}) is still tentative. Confirm or change the date
                {items.length > 1 ? ` · ${items.length - 1} more` : ''}.
            </span>
            <span className="shrink-0 font-medium">Calendar →</span>
        </Link>
    );
};

export default TentativeHolidayBanner;
