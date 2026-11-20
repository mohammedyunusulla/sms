/**
 * A submission's photos: the notebook page at the start (blank, with its QR sticker) and the finished pages.
 * The photo endpoint needs the login token, so each photo is fetched as a Blob. Tap a photo to enlarge it.
 */
import { useEffect, useState } from 'react';
import { homeworkApi } from '../api/homeworkApi';

interface SessionPhotosProps {
  sessionId: number;
  hasStartPhoto: boolean;
  pageCount: number;
}

export default function SessionPhotos({ sessionId, hasStartPhoto, pageCount }: SessionPhotosProps) {
  const [start, setStart] = useState<string | null>(null);
  const [pages, setPages] = useState<string[]>([]);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const created: string[] = [];
    setFailed(false);
    const load = async () => {
      try {
        const startBlob = hasStartPhoto ? await homeworkApi.getSessionPhoto(sessionId, 'start', 0) : null;
        const pageBlobs = await Promise.all(
          Array.from({ length: pageCount }, (_, index) => homeworkApi.getSessionPhoto(sessionId, 'page', index))
        );
        if (cancelled) return;
        if (startBlob) {
          const url = URL.createObjectURL(startBlob);
          created.push(url);
          setStart(url);
        }
        const pageUrls = pageBlobs.map((blob) => URL.createObjectURL(blob));
        created.push(...pageUrls);
        setPages(pageUrls);
      } catch {
        if (!cancelled) setFailed(true);
      }
    };
    void load();
    return () => {
      cancelled = true;
      created.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [sessionId, hasStartPhoto, pageCount]);

  if (failed) return <p className="text-sm text-red-600 dark:text-red-400">Couldn't load the photos.</p>;

  const thumb = (url: string, alt: string) => (
    <button key={url} type="button" onClick={() => setOpen(url)} className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700" title="Tap to enlarge">
      <img src={url} alt={alt} className="h-28 w-28 object-cover" />
    </button>
  );

  return (
    <div className="space-y-3" data-testid="session-photos">
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">At the start (blank page)</p>
        {hasStartPhoto ? (start ? thumb(start, 'Page at the start') : <div className="h-28 w-28 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />)
          : <p className="text-sm text-gray-500">No start photo (started before page QR codes were used).</p>}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Submitted pages</p>
        {pageCount === 0 ? <p className="text-sm text-gray-500">Not submitted yet.</p> : (
          <div className="flex flex-wrap gap-2">
            {pages.length === 0
              ? Array.from({ length: pageCount }, (_, i) => <div key={i} className="h-28 w-28 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />)
              : pages.map((url, index) => thumb(url, `Submitted page ${index + 1}`))}
          </div>
        )}
      </div>
      {open && (
        <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 p-4" onClick={() => setOpen(null)} role="dialog" aria-label="Photo">
          <img src={open} alt="Photo (enlarged)" className="max-h-[90vh] max-w-full rounded-lg" />
        </div>
      )}
    </div>
  );
}
