/**
 * Photo picker: "Take photo" or "Upload photo", with thumbnails and per-photo remove. Used for homework
 * photos (the board, the QR-stickered notebook page, finished pages).
 *
 * "Take photo" opens the phone's own camera app on phones (a focused, full-resolution photo; a frame grabbed
 * from the in-page video was too soft to read a small QR sticker) and the in-page camera on laptops.
 * Big photos are shrunk in the browser to 2560px on the long side so uploads stay small (the server's proxy
 * may cap request size) while staying sharper than the old 1920px video frame.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';

const MAX_BYTES = 8 * 1024 * 1024;
const SHRINK_ABOVE_BYTES = 1.5 * 1024 * 1024;
const MAX_SIDE = 2560;

// phones / tablets (touch is the main input): the native camera app is the better camera
const prefersNativeCamera = () => typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: coarse)').matches;

/** A smaller JPEG copy of a big photo (orientation kept); the original if it can't be decoded here. */
async function shrinkPhoto(file: File): Promise<File> {
  if (file.size <= SHRINK_ABOVE_BYTES || typeof createImageBitmap !== 'function') return file;
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
  } catch {
    return file; // e.g. a HEIC photo this browser can't decode: send it as it is
  }
}

interface PhotoPickerProps {
  photos: File[];
  onChange: (photos: File[]) => void;
  max?: number;
  label?: string;
  disabled?: boolean;
  /** a hint under the buttons, e.g. how to photograph a QR sticker */
  tip?: string;
}

export default function PhotoPicker({ photos, onChange, max = 5, label = 'Photos', disabled = false, tip }: PhotoPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const previews = useMemo(() => photos.map((file) => URL.createObjectURL(file)), [photos]);
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  const remaining = max - photos.length;

  const addFiles = async (picked: File[]) => {
    const accepted: File[] = [];
    const files = await Promise.all(picked.map((file) => (file.type.startsWith('image/') ? shrinkPhoto(file) : file)));
    for (const file of files) {
      if (!file.type.startsWith('image/')) {
        toast.error(`"${file.name}" is not a photo`);
        continue;
      }
      if (file.size > MAX_BYTES) {
        toast.error(`"${file.name}" is larger than 8 MB`);
        continue;
      }
      accepted.push(file);
    }
    if (accepted.length > remaining) {
      toast.error(`You can add up to ${max} photos`);
    }
    if (accepted.length) onChange([...photos, ...accepted.slice(0, Math.max(remaining, 0))]);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400">({photos.length}/{max})</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => (prefersNativeCamera() ? cameraInputRef.current?.click() : setCameraOpen(true))}
          disabled={disabled || remaining <= 0}
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          📷 Take photo
        </button>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || remaining <= 0}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          🖼 Upload photo
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          data-testid="photo-upload-input"
          onChange={(event) => {
            void addFiles(Array.from(event.target.files || []));
            event.target.value = '';
          }}
        />
        {/* phones: the camera app's own photo */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          data-testid="photo-camera-input"
          onChange={(event) => {
            void addFiles(Array.from(event.target.files || []));
            event.target.value = '';
          }}
        />
      </div>
      {tip && <p className="text-xs text-gray-500 dark:text-gray-400">{tip}</p>}

      {photos.length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid="photo-thumbnails">
          {previews.map((url, index) => (
            <div key={url} className="relative h-20 w-20 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
              <img src={url} alt={`Photo ${index + 1}`} className="h-full w-full object-cover" />
              <button
                type="button"
                onClick={() => onChange(photos.filter((_, i) => i !== index))}
                className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-xs text-white hover:bg-black/80"
                aria-label={`Remove photo ${index + 1}`}
                title="Remove"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {cameraOpen && (
        <CameraCapture
          tip={tip}
          onCapture={(file) => {
            void addFiles([file]);
            setCameraOpen(false);
          }}
          onClose={() => setCameraOpen(false)}
        />
      )}
    </div>
  );
}

function CameraCapture({ onCapture, onClose, tip }: { onCapture: (file: File) => void; onClose: () => void; tip?: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('This browser can\'t open the camera here (it needs HTTPS). Use "Upload photo" instead.');
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 3840 }, height: { ideal: 2160 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
        }
        setReady(true);
      } catch (err) {
        const name = (err as { name?: string })?.name;
        setError(
          name === 'NotAllowedError'
            ? 'Camera permission was denied. Allow the camera in the browser, or use "Upload photo".'
            : 'No camera could be opened. Use "Upload photo" instead.'
        );
      }
    };
    void start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  const capture = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(new File([blob], `photo-${Date.now()}.jpg`, { type: 'image/jpeg' }));
      },
      'image/jpeg',
      0.9
    );
  };

  return (
    <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/70 p-4" role="dialog" aria-label="Take photo">
      <div className="w-full max-w-2xl rounded-xl bg-white p-4 dark:bg-gray-900">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">Take photo</h3>
          <button type="button" onClick={onClose} className="text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400" aria-label="Close camera">
            ✕
          </button>
        </div>
        {error ? (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200">{error}</p>
        ) : (
          <video ref={videoRef} playsInline muted className="max-h-[60vh] w-full rounded-lg bg-black object-contain" />
        )}
        {!error && tip && <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{tip}</p>}
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-200">
            Cancel
          </button>
          {!error && (
            <button
              type="button"
              onClick={capture}
              disabled={!ready}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              Capture
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
