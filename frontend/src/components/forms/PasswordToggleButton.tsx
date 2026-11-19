/**
 * Eye button that shows / hides a password field.
 * Put it inside a `relative` wrapper next to the input, and give the input `pr-11` so text
 * doesn't run under the icon:
 *
 *   <div className="relative">
 *     <input type={visible ? 'text' : 'password'} className="... pr-11" />
 *     <PasswordToggleButton visible={visible} onToggle={() => setVisible((v) => !v)} />
 *   </div>
 */
import { FC } from 'react';

interface PasswordToggleButtonProps {
    visible: boolean;
    onToggle: () => void;
    disabled?: boolean;
}

const PasswordToggleButton: FC<PasswordToggleButtonProps> = ({ visible, onToggle, disabled = false }) => (
    <button
        type="button"
        onClick={onToggle}
        disabled={disabled}
        className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-500 hover:text-gray-700 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-200"
        aria-label={visible ? 'Hide password' : 'Show password'}
        title={visible ? 'Hide password' : 'Show password'}
    >
        {visible ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 3l18 18M10.58 10.58a2 2 0 002.83 2.83M9.88 4.24A9.77 9.77 0 0112 4c4.48 0 8.27 2.94 9.54 7a9.96 9.96 0 01-2.04 3.36M6.1 6.1A9.95 9.95 0 002.46 11c1.27 4.06 5.06 7 9.54 7 1.6 0 3.11-.37 4.45-1.04" />
            </svg>
        ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.46 12C3.73 7.94 7.52 5 12 5c4.48 0 8.27 2.94 9.54 7-1.27 4.06-5.06 7-9.54 7-4.48 0-8.27-2.94-9.54-7z" />
            </svg>
        )}
    </button>
);

export default PasswordToggleButton;
