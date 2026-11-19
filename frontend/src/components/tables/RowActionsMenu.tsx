import {
  FC,
  ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';

export interface RowAction {
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  variant?: 'default' | 'primary' | 'info' | 'success' | 'danger';
  /** When true the item is not rendered (use for permission gating). */
  hidden?: boolean;
  disabled?: boolean;
}

interface RowActionsMenuProps {
  items: RowAction[];
  /** Accessible name for the trigger. */
  label?: string;
  /** Approx. menu width in px (for right-edge positioning). */
  width?: number;
}

const VARIANT_CLASSES: Record<NonNullable<RowAction['variant']>, string> = {
  default: 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/[0.06]',
  primary: 'text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-500/10',
  info: 'text-blue-light-600 dark:text-blue-light-500 hover:bg-blue-light-50 dark:hover:bg-blue-light-500/10',
  success: 'text-success-600 dark:text-success-500 hover:bg-success-50 dark:hover:bg-success-500/10',
  danger: 'text-error-600 dark:text-error-500 hover:bg-error-50 dark:hover:bg-error-500/10',
};

const ROW_HEIGHT = 40; // approx px per item, for flip estimation

/**
 * Self-contained row actions (⋮) menu: encapsulates the trigger, viewport-aware
 * flip positioning, close-on-scroll/resize/outside-click/Escape and keyboard
 * navigation — replacing the ~70-line hand-rolled menus duplicated across list
 * pages. Declare actions as data via `items`.
 */
const RowActionsMenu: FC<RowActionsMenuProps> = ({ items, label = 'More actions', width = 192 }) => {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top?: number; bottom?: number; right: number }>({ right: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const visible = items.filter((i) => !i.hidden);

  const place = useCallback(() => {
    const btn = triggerRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const menuHeight = visible.length * ROW_HEIGHT + 8;
    const spaceBelow = window.innerHeight - rect.bottom;
    const right = window.innerWidth - rect.right;
    if (spaceBelow >= menuHeight) {
      setPos({ top: rect.bottom + 4, right });
    } else {
      setPos({ bottom: window.innerHeight - rect.top + 4, right });
    }
  }, [visible.length]);

  // Position synchronously before paint to avoid a flash at (0,0).
  useLayoutEffect(() => {
    if (open) place();
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && menuRef.current) {
        e.preventDefault();
        const buttons = Array.from(menuRef.current.querySelectorAll<HTMLButtonElement>('button'));
        if (!buttons.length) return;
        const idx = buttons.indexOf(document.activeElement as HTMLButtonElement);
        const next = e.key === 'ArrowDown'
          ? (idx + 1) % buttons.length
          : (idx - 1 + buttons.length) % buttons.length;
        buttons[next].focus();
      }
    };
    // Close when the page scrolls (menu is position:fixed and would detach).
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    document.addEventListener('keydown', onKey);
    // Focus first item once open.
    menuRef.current?.querySelector<HTMLButtonElement>('button')?.focus();
    return () => {
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('resize', close);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (visible.length === 0) return null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        className="p-2 rounded-lg text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
      >
        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="5" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="19" r="2" />
        </svg>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            ref={menuRef}
            role="menu"
            style={{
              width,
              top: pos.top !== undefined ? `${pos.top}px` : undefined,
              bottom: pos.bottom !== undefined ? `${pos.bottom}px` : undefined,
              right: `${pos.right}px`,
            }}
            className="fixed z-50 overflow-hidden rounded-xl border border-gray-200 bg-white py-1 shadow-theme-lg animate-slide-up-fade dark:border-gray-800 dark:bg-gray-900"
          >
            {visible.map((item, i) => (
              <button
                key={i}
                role="menuitem"
                disabled={item.disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  setOpen(false);
                  item.onClick();
                }}
                className={`flex w-full items-center gap-2 px-4 py-2 text-left text-theme-sm transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none ${VARIANT_CLASSES[item.variant || 'default']}`}
              >
                {item.icon && <span className="shrink-0">{item.icon}</span>}
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  );
};

export default RowActionsMenu;
