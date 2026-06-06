import { useCallback, useEffect, useState } from 'react';
import { ImageResultDTO } from '@/api/types';
import { api, imageUrl } from '@/api/client';
import { Button } from '@/components/common/Button';
import { X, ChevronLeft, ChevronRight, FolderOpen, Download, Copy } from 'lucide-react';

interface ImageLightboxProps {
  images: ImageResultDTO[];
  initialIndex: number;
  onClose: () => void;
}

export function ImageLightbox({ images, initialIndex, onClose }: ImageLightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const current = images[index];

  useEffect(() => {
    if (index >= images.length) setIndex(0);
  }, [images.length, index]);

  const handleNext = useCallback(() => {
    setIndex((prev) => (prev + 1) % images.length);
  }, [images.length]);

  const handlePrev = useCallback(() => {
    setIndex((prev) => (prev - 1 + images.length) % images.length);
  }, [images.length]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') handleNext();
      if (e.key === 'ArrowLeft') handlePrev();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNext, handlePrev, onClose]);

  if (!current) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex flex-col animate-in fade-in duration-200">
      <div className="h-16 flex items-center justify-between px-6 border-b border-white/10">
        <span className="text-sm font-mono text-text-muted">
            {index + 1} / {images.length} • {current.file_path.split(/[/\\]/).pop()}
        </span>
        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
            <X size={24} />
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center relative p-8">
        <img 
            src={imageUrl(current.file_path)} 
            className="max-w-full max-h-full object-contain shadow-2xl rounded-sm"
            alt="Full size"
        />
        
        {images.length > 1 && (
            <>
                <button onClick={handlePrev} className="absolute left-4 p-3 rounded-full bg-black/50 hover:bg-white/20 transition-colors backdrop-blur-sm">
                    <ChevronLeft size={32} />
                </button>
                <button onClick={handleNext} className="absolute right-4 p-3 rounded-full bg-black/50 hover:bg-white/20 transition-colors backdrop-blur-sm">
                    <ChevronRight size={32} />
                </button>
            </>
        )}
      </div>

      <div className="h-20 border-t border-white/10 flex items-center justify-center gap-4 bg-black/40">
        <Button variant="secondary" onClick={() => api.openPath(current.file_path)}>
            <FolderOpen size={16} className="mr-2" /> Show in Finder
        </Button>
        <Button variant="secondary" onClick={() => navigator.clipboard.writeText(current.file_path)}>
            <Copy size={16} className="mr-2" /> Copy Path
        </Button>
        <Button variant="primary" onClick={async () => {
            const res = await api.selectFolder();
            if (res.path) {
                await api.export([current.row_id], res.path);
            }
        }}>
            <Download size={16} className="mr-2" /> Export
        </Button>
      </div>
    </div>
  );
}
