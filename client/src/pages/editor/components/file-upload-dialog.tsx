import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Icons } from "@/components/shared/icons";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { IImage, IVideo, IAudio } from "@designcombo/types";
import { generateId } from "@designcombo/timeline";

interface FileUploadDialogProps {
  onUpload: (files: Array<Partial<IImage | IVideo | IAudio>>) => void;
  trigger?: React.ReactNode;
}

export function FileUploadDialog({ onUpload, trigger }: FileUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  // Function to generate a thumbnail from a video
  const generateVideoThumbnail = (videoFile: File): Promise<string> => {
    return new Promise((resolve) => {
      const video = document.createElement('video');
      const url = URL.createObjectURL(videoFile);
      
      video.onloadeddata = () => {
        // Seek to 1 second or the middle of the video
        video.currentTime = Math.min(1, video.duration / 2);
      };
      
      video.onseeked = () => {
        // Create a canvas to draw the video frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw the video frame on the canvas
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert the canvas to a data URL
        const thumbnailUrl = canvas.toDataURL('image/jpeg');
        
        // Clean up
        URL.revokeObjectURL(url);
        
        resolve(thumbnailUrl);
      };
      
      // Handle errors
      video.onerror = () => {
        console.error('Error generating video thumbnail');
        URL.revokeObjectURL(url);
        resolve(''); // Return empty string on error
      };
      
      video.src = url;
      video.load();
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    
    setUploading(true);
    
    try {
      // Process files and generate thumbnails for videos
      const uploadedFiles = await Promise.all(
        files.map(async (file) => {
          const url = URL.createObjectURL(file);
          const id = generateId();
          
          // Determine file type
          if (file.type.startsWith('image/')) {
            return {
              id,
              type: 'image' as const,
              details: { 
                src: url,
                brightness: 100,
                opacity: 100,
                blur: 0
              },
              preview: url,
              name: file.name,
            };
          } else if (file.type.startsWith('video/')) {
            // Generate thumbnail for video
            const thumbnailUrl = await generateVideoThumbnail(file);
            
            return {
              id,
              type: 'video' as const,
              details: { 
                src: url,
                brightness: 100,
                opacity: 100,
                blur: 0
              },
              preview: thumbnailUrl || url, // Use thumbnail or fallback to video URL
              name: file.name,
              duration: 0, // This would be determined by the server in a real app
            };
          } else if (file.type.startsWith('audio/')) {
            return {
              id,
              type: 'audio' as const,
              details: { src: url },
              name: file.name,
              metadata: {
                author: 'User Upload',
              },
            };
          }
          
          return null;
        })
      ).then(files => files.filter(Boolean) as Array<Partial<IImage | IVideo | IAudio>>);
      
      onUpload(uploadedFiles);
      setOpen(false);
      setFiles([]);
    } catch (error) {
      console.error('Error uploading files:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="ghost" size="icon">
            <Icons.upload width={18} />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Files</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div
            className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-12"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <Icons.upload className="mb-4 h-8 w-8 text-muted-foreground" />
            <p className="mb-2 text-sm text-muted-foreground">
              Drag and drop files here or click to browse
            </p>
            <Input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileChange}
              accept="image/*,video/*,audio/*"
            />
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              Browse Files
            </Button>
          </div>
          
          {files.length > 0 && (
            <div className="mt-4">
              <Label>Selected Files</Label>
              <div className="mt-2 max-h-40 overflow-y-auto rounded-md border border-border p-2">
                {files.map((file, index) => (
                  <div key={index} className="flex items-center justify-between py-1">
                    <span className="text-sm truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleUpload} disabled={files.length === 0 || uploading}>
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
