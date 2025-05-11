import React from "react";
import useLayoutStore from "../store/use-layout-store";
import {
  IAudio,
  IImage,
  IText,
  ITrackItem,
  ITrackItemAndDetails,
  IVideo,
} from "@designcombo/types";
import { useEffect, useState } from "react";
import Presets from "./presets";
import Animations from "./animations";
import Smart from "./smart";
import BasicText from "./basic-text";
import BasicImage from "./basic-image";
import BasicVideo from "./basic-video";
import BasicAudio from "./basic-audio";
import useStore from "../store/use-store";

const Container = ({ children }: { children: React.ReactNode }) => {
  const { activeToolboxItem } = useLayoutStore();
  const { activeIds, trackItemsMap, trackItemDetailsMap, transitionsMap } =
    useStore();
  const [trackItem, setTrackItem] = useState<ITrackItem | null>(null);
  const [displayToolbox, setDisplayToolbox] = useState<boolean>(false);

  useEffect(() => {
    if (activeIds.length === 1) {
      const [id] = activeIds;
      const trackItemDetails = trackItemDetailsMap[id];
      const trackItem = {
        ...trackItemsMap[id],
        details: trackItemDetails?.details || {},
      };
      if (trackItemDetails) setTrackItem(trackItem);
      else console.log(transitionsMap[id]);
    } else {
      setTrackItem(null);
      setDisplayToolbox(false);
    }
  }, [activeIds, trackItemsMap]);

  useEffect(() => {
    if (activeToolboxItem) {
      setDisplayToolbox(true);
    } else {
      setDisplayToolbox(false);
    }
  }, [activeToolboxItem]);

  if (!trackItem || !displayToolbox) {
    return null;
  }

  return (
    <div className="h-full w-full overflow-y-auto p-2">
      {React.cloneElement(children as React.ReactElement, {
        trackItem,
        activeToolboxItem,
      })}
    </div>
  );
};

const ActiveControlItem = ({
  trackItem,
  activeToolboxItem,
}: {
  trackItem?: ITrackItemAndDetails;
  activeToolboxItem?: string;
}) => {
  if (!trackItem || !activeToolboxItem) {
    return null;
  }
  return (
    <>
      {
        {
          "basic-text": (
            <BasicText trackItem={trackItem as ITrackItem & IText} />
          ),
          "basic-image": (
            <BasicImage trackItem={trackItem as ITrackItem & IImage} />
          ),
          "basic-video": (
            <BasicVideo trackItem={trackItem as ITrackItem & IVideo} />
          ),
          "basic-audio": (
            <BasicAudio trackItem={trackItem as ITrackItem & IAudio} />
          ),
          "preset-text": <Presets />,
          animation: <Animations />,
          smart: <Smart />,
        }[activeToolboxItem]
      }
    </>
  );
};

export const ControlItem = () => {
  return (
    <Container>
      <ActiveControlItem />
    </Container>
  );
};
