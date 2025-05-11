import { ScrollArea } from "@/components/ui/scroll-area";
import { IMAGES } from "@/data/images";
import { dispatch } from "@designcombo/events";
import { generateId } from "@designcombo/timeline";
import Draggable from "@/components/shared/draggable";
import { IImage } from "@designcombo/types";
import React from "react";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import { ADD_ITEMS } from "@designcombo/state";
import { useUploadsContext } from "../context/uploads-context";

export const Images = () => {
  const isDraggingOverTimeline = useIsDraggingOverTimeline();
  const { getUploadedFilesByType } = useUploadsContext();
  
  const uploadedImages = getUploadedFilesByType('image') as Partial<IImage>[];

  const handleAddImage = (payload: Partial<IImage>) => {
    const id = generateId();
    // dispatch(ADD_IMAGE, {
    //   payload: {
    //     id,
    //     type: "image",
    //     display: {
    //       from: 5000,
    //       to: 10000,
    //     },
    //     details: {
    //       src: payload.details?.src,
    //     },
    //   },
    //   options: {
    //     scaleMode: "fit",
    //   },
    // });
    dispatch(ADD_ITEMS, {
      payload: {
        trackItems: [
          {
            id,
            type: "image",
            display: {
              from: 0,
              to: 5000,
            },
            details: {
              src: payload.details?.src,
            },
            metadata: {},
          },
        ],
      },
    });
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="text-text-primary flex h-12 flex-none items-center px-4 text-sm font-medium">
        Photos
      </div>
      <ScrollArea>
        <div className="grid grid-cols-2 gap-2 p-4">
          {/* User uploaded images */}
          {uploadedImages.length > 0 && (
            <>
              <div className="col-span-2 mt-2 mb-1 text-xs font-medium text-muted-foreground">
                Your Images
              </div>
              {uploadedImages.map((image, index) => (
                <ImageItem
                  key={`uploaded-${index}`}
                  image={image}
                  shouldDisplayPreview={!isDraggingOverTimeline}
                  handleAddImage={handleAddImage}
                />
              ))}
            </>
          )}
          
          {/* Stock images */}
          <div className="col-span-2 mt-4 mb-1 text-xs font-medium text-muted-foreground">
            Stock Images
          </div>
          {IMAGES.map((image, index) => (
            <ImageItem
              key={`stock-${index}`}
              image={image}
              shouldDisplayPreview={!isDraggingOverTimeline}
              handleAddImage={handleAddImage}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
};

const ImageItem = ({
  handleAddImage,
  image,
  shouldDisplayPreview,
}: {
  handleAddImage: (payload: Partial<IImage>) => void;
  image: Partial<IImage>;
  shouldDisplayPreview: boolean;
}) => {
  const style = React.useMemo(
    () => ({
      backgroundImage: `url(${image.preview})`,
      backgroundSize: "cover",
      width: "80px",
      height: "80px",
    }),
    [image.preview],
  );

  return (
    <Draggable
      data={image}
      renderCustomPreview={<div style={style} />}
      shouldDisplayPreview={shouldDisplayPreview}
    >
      <div
        onClick={() =>
          handleAddImage({
            id: generateId(),
            type: 'image',
            details: {
              src: image.details?.src || '',
              width: 1920,
              height: 1080,
              opacity: 1,
              transform: '',
              border: '',
              borderRadius: 0,
              boxShadow: { color: '', x: 0, y: 0, blur: 0 },
              top: '0',
              left: '0',
              transformOrigin: 'center center',
              crop: { x: 0, y: 0, width: 0, height: 0 },
              blur: 0,
              brightness: 1,
              flipX: false,
              flipY: false,
              rotate: '0deg',
              visibility: 'visible',
              background: ''
            },
            preview: image.preview,
            name: image.name || 'Image',
          })
        }
        className="flex w-full items-center justify-center overflow-hidden bg-background pb-2"
      >
        <img
          draggable={false}
          src={image.preview}
          className="h-full w-full rounded-md object-cover"
          alt="image"
        />
      </div>
    </Draggable>
  );
};
