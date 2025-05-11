import { Button } from "@/components/ui/button";
import { UploadIcon, FileIcon, FileVideoIcon, FileAudioIcon, FileImageIcon } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUploadsContext } from "../context/uploads-context";
import { IImage, IVideo, IAudio } from "@designcombo/types";
import { FileUploadDialog } from "../components/file-upload-dialog";
import Draggable from "@/components/shared/draggable";
import { dispatch } from "@designcombo/events";
import { ADD_VIDEO, ADD_IMAGE, ADD_AUDIO } from "@designcombo/state";
import { generateId } from "@designcombo/timeline";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import React from "react";

// Media item component
const MediaItem = ({ 
  item, 
  type 
}: { 
  item: Partial<IImage | IVideo | IAudio>; 
  type: 'image' | 'video' | 'audio' 
}) => {
  const isDraggingOverTimeline = useIsDraggingOverTimeline();
  
  const getIcon = () => {
    switch (type) {
      case 'image':
        return <FileImageIcon className="h-4 w-4" />;
      case 'video':
        return <FileVideoIcon className="h-4 w-4" />;
      case 'audio':
        return <FileAudioIcon className="h-4 w-4" />;
      default:
        return <FileIcon className="h-4 w-4" />;
    }
  };

  const getPreview = () => {
    if (type === 'image' && (item as Partial<IImage>).preview) {
      return (
        <img 
          draggable={false}
          src={(item as Partial<IImage>).preview} 
          alt={item.name || 'Image'} 
          className="h-full w-full object-cover"
        />
      );
    } else if (type === 'video' && (item as Partial<IVideo>).preview) {
      return (
        <div className="relative h-full w-full bg-muted">
          <img 
            draggable={false}
            src={(item as Partial<IVideo>).preview} 
            alt={item.name || 'Video'} 
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <FileVideoIcon className="h-8 w-8 text-white opacity-70" />
          </div>
        </div>
      );
    } else {
      return (
        <div className="flex h-full w-full items-center justify-center bg-muted">
          {getIcon()}
        </div>
      );
    }
  };

  const handleAddItem = () => {
    const id = generateId();
    
    switch (type) {
      case 'image':
        dispatch(ADD_IMAGE, {
          payload: {
            id,
            type: 'image',
              details: {
                src: (item as Partial<IImage>).details?.src || '',
                width: 1920,
                height: 1080,
                blur: 0,
                brightness: 100,
                opacity: 100,
                flipX: false,
                flipY: false,
                rotate: '0deg',
                visibility: 'visible'
              },
            preview: (item as Partial<IImage>).preview,
            name: item.name || 'Image',
          },
          options: {
            resourceId: "main",
            scaleMode: "fit",
          },
        });
        break;
      case 'video':
        dispatch(ADD_VIDEO, {
          payload: {
            id,
            type: 'video',
              details: {
                src: (item as Partial<IVideo>).details?.src || '',
                width: 1920,
                height: 1080,
                blur: 0,
                brightness: 100,
                opacity: 100,
                flipX: false,
                flipY: false,
                rotate: '0deg',
                visibility: 'visible'
              },
            preview: (item as Partial<IVideo>).preview,
            name: item.name || 'Video',
          },
          options: {
            resourceId: "main",
            scaleMode: "fit",
          },
        });
        break;
      case 'audio':
        dispatch(ADD_AUDIO, {
          payload: {
            id,
            type: 'audio',
            details: {
              src: (item as Partial<IAudio>).details?.src || '',
              volume: 100,
            },
            name: item.name || 'Audio',
          },
        });
        break;
    }
  };

  const style = React.useMemo(
    () => ({
      backgroundImage: `url(${item.preview})`,
      backgroundSize: "cover",
      width: "80px",
      height: "80px",
    }),
    [item.preview],
  );

  return (
    <Draggable
      data={{
        ...item,
        metadata: {
          previewUrl: item.preview,
        },
      }}
      renderCustomPreview={<div style={style} className="draggable" />}
      shouldDisplayPreview={!isDraggingOverTimeline}
    >
      <div 
        className="group relative mb-3 h-24 w-full cursor-pointer overflow-hidden rounded-md border border-border"
        onClick={handleAddItem}
      >
        {getPreview()}
        <div className="absolute bottom-0 left-0 right-0 bg-background/80 p-1 text-xs backdrop-blur-sm">
          {item.name || 'Untitled'}
        </div>
      </div>
    </Draggable>
  );
};

export const Uploads = () => {
  const { uploadedFiles, addUploadedFiles } = useUploadsContext();
  
  const handleUpload = (files: Array<Partial<IImage | IVideo | IAudio>>) => {
    addUploadedFiles(files);
  };
  return (
    <div className="flex flex-1 flex-col">
      <div className="text-text-primary flex h-12 flex-none items-center px-4 text-sm font-medium">
        Your media
      </div>
      <div className="px-4 py-2">
        <FileUploadDialog
          onUpload={handleUpload}
          trigger={
            <Button
              className="flex w-full gap-2"
              variant="secondary"
            >
              <UploadIcon size={16} /> Upload
            </Button>
          }
        />
      </div>
      <ScrollArea className="flex-1">
        <div className="grid grid-cols-2 gap-2 p-4">
          {uploadedFiles.map((file, index) => (
            <MediaItem 
              key={index} 
              item={file} 
              type={file.type as 'image' | 'video' | 'audio'} 
            />
          ))}
          {uploadedFiles.length === 0 && (
            <div className="col-span-2 flex h-24 items-center justify-center text-sm text-muted-foreground">
              No uploaded files yet
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
