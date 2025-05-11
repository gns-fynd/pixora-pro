import Draggable from "@/components/shared/draggable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { VIDEOS } from "@/data/video";
import { dispatch } from "@designcombo/events";
import { ADD_VIDEO } from "@designcombo/state";
import { generateId } from "@designcombo/timeline";
import { IVideo } from "@designcombo/types";
import React from "react";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import { useUploadsContext } from "../context/uploads-context";

export const Videos = () => {
  const isDraggingOverTimeline = useIsDraggingOverTimeline();
  const { getUploadedFilesByType } = useUploadsContext();
  
  const uploadedVideos = getUploadedFilesByType('video') as Partial<IVideo>[];

  const handleAddVideo = (payload: Partial<IVideo>) => {
    dispatch(ADD_VIDEO, {
      payload,
      options: {
        resourceId: "main",
        scaleMode: "fit",
      },
    });
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="text-text-primary flex h-12 flex-none items-center px-4 text-sm font-medium">
        Videos
      </div>
      <ScrollArea>
        <div className="grid grid-cols-2 gap-2 p-4">
          {/* User uploaded videos */}
          {uploadedVideos.length > 0 && (
            <>
              <div className="col-span-2 mt-2 mb-1 text-xs font-medium text-muted-foreground">
                Your Videos
              </div>
              {uploadedVideos.map((video, index) => (
                <VideoItem
                  key={`uploaded-${index}`}
                  video={video}
                  shouldDisplayPreview={!isDraggingOverTimeline}
                  handleAddImage={handleAddVideo}
                />
              ))}
            </>
          )}
          
          {/* Stock videos */}
          <div className="col-span-2 mt-4 mb-1 text-xs font-medium text-muted-foreground">
            Stock Videos
          </div>
          {VIDEOS.map((video, index) => (
            <VideoItem
              key={`stock-${index}`}
              video={video}
              shouldDisplayPreview={!isDraggingOverTimeline}
              handleAddImage={handleAddVideo}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
};

const VideoItem = ({
  handleAddImage,
  video,
  shouldDisplayPreview,
}: {
  handleAddImage: (payload: Partial<IVideo>) => void;
  video: Partial<IVideo>;
  shouldDisplayPreview: boolean;
}) => {
  const style = React.useMemo(
    () => ({
      backgroundImage: `url(${video.preview})`,
      backgroundSize: "cover",
      width: "80px",
      height: "80px",
    }),
    [video.preview],
  );

  return (
    <Draggable
      data={{
        ...video,
        metadata: {
          previewUrl: video.preview,
        },
      }}
      renderCustomPreview={<div style={style} className="draggable" />}
      shouldDisplayPreview={shouldDisplayPreview}
    >
      <div
        onClick={() =>
          handleAddImage({
            id: generateId(),
            type: 'video',
            details: {
              src: video.details?.src || '',
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
            preview: video.preview,
            name: video.name || 'Video',
          })
        }
        className="flex w-full items-center justify-center overflow-hidden bg-background pb-2"
      >
        <img
          draggable={false}
          src={video.preview}
          className="h-full w-full rounded-md object-cover"
          alt="image"
        />
      </div>
    </Draggable>
  );
};
