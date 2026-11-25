/**
 * The (i) button beside a page title and its short "About this page" box (text: config/pageHelp.ts).
 */
import { FC, useState } from 'react';
import Modal from '../modals/Modal';
import type { PageHelp } from '../../config/pageHelp';

const PageInfo: FC<{ title: string; help: PageHelp }> = ({ title, help }) => {
    const [open, setOpen] = useState(false);
    return (
        <>
            <button type="button" aria-label={`About ${title}`} title={`About ${title}`} onClick={() => setOpen(true)}
                className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-blue-50 hover:text-blue-600 dark:text-gray-500 dark:hover:bg-gray-700 dark:hover:text-blue-400">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
                    <circle cx="12" cy="12" r="9" />
                    <path strokeLinecap="round" d="M12 11v5" />
                    <circle cx="12" cy="7.75" r="0.6" fill="currentColor" />
                </svg>
            </button>
            <Modal isOpen={open} onClose={() => setOpen(false)} title={`About ${title.toLowerCase()}`} size="md">
                <div className="space-y-3 text-sm font-normal text-gray-700 dark:text-gray-300" data-testid="page-info">
                    <p className="font-medium text-gray-900 dark:text-white">{help.lead}</p>
                    <ul className="list-disc space-y-1.5 pl-5">
                        {help.points.map((p) => <li key={p}>{p}</li>)}
                    </ul>
                    <p className="rounded-lg bg-gray-50 px-3 py-2 text-gray-600 dark:bg-gray-700/50 dark:text-gray-300">
                        <span className="font-medium text-gray-900 dark:text-white">Example:</span> {help.example}
                    </p>
                </div>
            </Modal>
        </>
    );
};

export default PageInfo;
