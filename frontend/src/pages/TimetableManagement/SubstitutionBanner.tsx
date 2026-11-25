/**
 * Dashboard strip for timetable managers: periods that still need a substitute today.
 */
import { FC, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { substitutionService } from '../../services/modules/substitutionService';

const SubstitutionBanner: FC = () => {
    const [uncovered, setUncovered] = useState(0);

    useEffect(() => {
        let alive = true;
        substitutionService.today().then((d) => alive && setUncovered(d.uncovered)).catch(() => undefined);
        return () => {
            alive = false;
        };
    }, []);

    if (!uncovered) return null;
    return (
        <Link to="/substitutions"
            className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 transition-colors hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-200 dark:hover:bg-blue-900/30">
            <span><strong>{uncovered}</strong> period{uncovered === 1 ? '' : 's'} need{uncovered === 1 ? 's' : ''} a substitute today</span>
            <span className="shrink-0 font-medium">Arrange →</span>
        </Link>
    );
};

export default SubstitutionBanner;
