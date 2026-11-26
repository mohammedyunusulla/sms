/**
 * The finished pages a student submitted. The photo endpoint needs the login token, so each photo is fetched
 * as a Blob. Tap a photo to enlarge it.
 */
import { useEffect, useState } from 'react';
import { homeworkApi } from '../api/homeworkApi';

interface SessionPhotosProps {
  sessionId: number;
  pageCount: number;
}

export default function SessionPhotos({ sessionId, pageCount }: SessionPhotosProps) {
  const [pages, setPages] = useState<string[]>([]);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    setFailed(false);
    setPages([]);
    Promise.all(Array.from({ length: pageCount }, (_, index) => homeworkApi.getSessionPage(sessionId, index)))
      .then((blobs) => {
        if (cancelled) return;
        const urls = blobs.map((blob) => URL.createObjectURL(blob));
        created.push(...urls);
        setPages(urls);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      created.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [sessionId, pageCount]);

  if (failed) return <p className="text-sm text-red-600 dark:text-red-400">Couldn't load the photos.</p>;

  return (
    <div data-testid="session-photos">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Submitted pages</p>
      {pageCount === 0 ? <p className="text-sm text-gray-500">No photos.</p> : (
        <div className="flex flex-wrap gap-2">
          {pages.length === 0
            ? Array.from({ length: pageCount }, (_, i) => <div key={i} className="h-28 w-28 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />)
            : pages.map((url, index) => (
              <button key={url} type="button" onClick={() => setOpen(url)} title="Tap to enlarge"
                className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <img src={url} alt={`Submitted page ${index + 1}`} className="h-28 w-28 object-cover" />
              </button>
            ))}
        </div>
      )}
      {open && (
        <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 p-4" onClick={() => setOpen(null)} role="dialog" aria-label="Photo">
          <img src={open} alt="Photo (enlarged)" className="max-h-[90vh] max-w-full rounded-lg" />
        </div>
      )}
    </div>
  );
}
