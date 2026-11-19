import { FC } from 'react';

interface IMandatoryIndicatorProps {
    className?: string;
}

/**
 * MandatoryIndicator
 * Renders the red asterisk used to mark required form fields.
 * Use inline next to a label, e.g. `Email <MandatoryIndicator />`.
 */
const MandatoryIndicator: FC<IMandatoryIndicatorProps> = ({ className = '' }) => (
    <span className={`text-red-500 ${className}`.trim()}>*</span>
);

export default MandatoryIndicator;
