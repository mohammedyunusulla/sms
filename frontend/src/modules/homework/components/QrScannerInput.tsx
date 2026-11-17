import { useEffect, useMemo, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';

interface QrScannerInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  idSeed: string;
}

export default function QrScannerInput({ label, value, onChange, idSeed }: QrScannerInputProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState('');
  const qrRef = useRef<Html5Qrcode | null>(null);
  const elementId = useMemo(() => `qr-reader-${idSeed}`, [idSeed]);

  useEffect(() => {
    return () => {
      if (qrRef.current) {
        qrRef.current.stop().catch(() => undefined);
        qrRef.current.clear().catch(() => undefined);
      }
    };
  }, []);

  const startScanner = async () => {
    setScanError('');
    try {
      const instance = new Html5Qrcode(elementId);
      qrRef.current = instance;
      await instance.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decodedText) => {
          onChange(decodedText.trim());
          stopScanner();
        }
      );
      setIsScanning(true);
    } catch (error: any) {
      setScanError(error?.message || 'Unable to start scanner.');
    }
  };

  const stopScanner = async () => {
    if (!qrRef.current) return;
    await qrRef.current.stop().catch(() => undefined);
    await qrRef.current.clear().catch(() => undefined);
    qrRef.current = null;
    setIsScanning(false);
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</label>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Scan sticker or enter manually"
        className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
      />
      <div className="flex gap-2">
        {!isScanning ? (
          <button
            type="button"
            onClick={startScanner}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Open Camera Scanner
          </button>
        ) : (
          <button
            type="button"
            onClick={stopScanner}
            className="rounded-lg bg-gray-700 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            Stop Scanner
          </button>
        )}
      </div>
      <div id={elementId} className={isScanning ? 'w-full max-w-sm overflow-hidden rounded-lg border border-gray-200' : 'hidden'} />
      {scanError && <p className="text-sm text-red-600">{scanError}</p>}
    </div>
  );
}
