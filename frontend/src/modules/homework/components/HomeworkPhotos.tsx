/**
 * Shows a homework's photos (e.g. the board). The photo endpoint needs the login token,
 * so each photo is fetched as a Blob and shown from an object URL. Tap a photo to enlarge it.
 */
import { useEffect, useState } from 'react';
import { homeworkApi } from '../api/homeworkApi';

export default function HomeworkPhotos({ homeworkId, count }: { homeworkId: number; count: number }) {
  const [urls, setUrls] = useState<string[]>([]);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    if (!count) {
      setUrls([]);
      return;
    }
    let cancelled = false;
    const created: string[] = [];
    setFailed(false);
    Promise.all(Array.from({ length: count }, (_, index) => homeworkApi.getHomeworkPhoto(homeworkId, index)))
      .then((blobs) => {
        if (cancelled) return;
        blobs.forEach((blob) => created.push(URL.createObjectURL(blob)));
        setUrls(created);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      created.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [homeworkId, count]);

  if (!count) return null;
  if (failed) return <p className="text-sm text-red-600 dark:text-red-400">Couldn't load the homework photos.</p>;

  return (
    <>
      <div className="flex flex-wrap gap-2" data-testid="homework-photos">
        {urls.length === 0
          ? Array.from({ length: count }, (_, i) => <div key={i} className="h-24 w-24 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />)
          : urls.map((url, index) => (
              <button key={url} type="button" onClick={() => setOpen(url)} className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700" title="Tap to enlarge">
                <img src={url} alt={`Homework photo ${index + 1}`} className="h-24 w-24 object-cover" />
              </button>
            ))}
      </div>
      {open && (
        <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 p-4" onClick={() => setOpen(null)} role="dialog" aria-label="Homework photo">
          <img src={open} alt="Homework photo (enlarged)" className="max-h-[90vh] max-w-full rounded-lg" />
        </div>
      )}
    </>
  );
}
