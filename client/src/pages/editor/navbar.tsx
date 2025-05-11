import { useEffect, useState } from "react";
import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { dispatch } from "@designcombo/events";
import { DESIGN_RESIZE } from "@designcombo/state";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ChevronDown, Download } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { download } from "@/utils/download";
import { Icons } from "@/components/shared/icons";
import useStore from "@/pages/editor/store/use-store";
import { generateId } from "@designcombo/timeline";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
const baseUrl = "https://renderer.designcombo.dev";
const size = {
  width: 1080,
  height: 1920,
};
//  https://renderer.designcombo.dev/status/{id}
export default function Navbar() {
  const { theme } = useTheme();
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
      }}
      className="pointer-events-none fixed left-0 right-0 top-0 z-[205] flex h-[72px] items-center px-4 glass-morphism-light"
    >
      <div className="pointer-events-auto flex h-14 items-center gap-2">
        {/* Left section - Pixora Logo */}
        <div className="flex items-center">
        <div className="relative w-24">
            <img 
              src={theme === "dark" ? "./logo-light.png" : "./logo-dark.png"} 
              alt="Pixora AI" 
              className="relative w-24 ml-12"
            />
          </div>
        </div>
      </div>

      <div className="pointer-events-auto flex h-14 items-center justify-center gap-2">
        <div className="flex h-12 items-center gap-4 rounded-md glass-morphism px-2.5">
          <div className="px-1 text-sm font-medium">Untitled video</div>
          <ResizeVideo />
        </div>
      </div>

      <div className="pointer-events-auto flex h-14 items-center justify-end gap-2">
        <div className="flex h-12 items-center gap-2 rounded-md glass-morphism px-2.5">
          <ThemeToggle />
          <DownloadPopover />
        </div>
      </div>
    </div>
  );
}

interface IDownloadState {
  renderId: string;
  progress: number;
  isDownloading: boolean;
}
const DownloadPopover = () => {
  const [open, setOpen] = useState(false);
  const [downloadState, setDownloadState] = useState<IDownloadState>({
    progress: 0,
    isDownloading: false,
    renderId: "",
  });
  const {
    tracks,
    trackItemIds,
    trackItemsMap,
    trackItemDetailsMap,
    transitionsMap,
    transitionIds,
    fps,
  } = useStore();

  const handleExport = () => {
    const data = {
      id: generateId(),
      fps,
      tracks,
      size,
      trackItemDetailsMap,
      trackItemIds,
      transitionsMap,
      trackItemsMap,
      transitionIds,
    };
    console.log(data);
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (downloadState.renderId) {
      interval = setInterval(() => {
        fetch(`${baseUrl}/status/${downloadState.renderId}`)
          .then((res) => res.json())
          .then(({ render: { progress, output } }) => {
            if (progress === 100) {
              clearInterval(interval);
              setDownloadState({
                ...downloadState,
                renderId: "",
                progress: 0,
                isDownloading: false,
              });
              download(output, `${downloadState.renderId}`);
              setOpen(false);
            } else {
              setDownloadState({
                ...downloadState,
                progress,
                isDownloading: true,
              });
            }
          });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [downloadState.renderId]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          className="flex h-9 w-9 gap-1 border border-border/20 bg-primary/90 hover:bg-primary text-white"
          size="icon"
          variant="secondary"
        >
          <Download width={18} />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="z-[250] flex w-60 flex-col gap-4">
        {downloadState.isDownloading ? (
          <>
            <Label>Downloading</Label>
            <div className="flex items-center gap-2">
              <Progress
                className="h-2 rounded-sm bg-muted [&>div]:bg-primary"
                value={downloadState.progress}
              />
              <div className="rounded-sm border border-border p-1 text-sm text-zinc-400">
                {parseInt(downloadState.progress.toString())}%
              </div>
            </div>
            <div>
              <Button className="w-full bg-primary/90 hover:bg-primary text-white">Copy link</Button>
            </div>
          </>
        ) : (
          <>
            <Label>Export settings</Label>
            <Button className="w-full justify-between" variant="outline">
              <div>MP4</div>
              <ChevronDown width={16} />
            </Button>
            <div>
              <Button onClick={handleExport} className="w-full bg-primary/90 hover:bg-primary text-white">
                Export
              </Button>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  );
};

interface ResizeOptionProps {
  label: string;
  icon: string;
  value: ResizeValue;
  description: string;
}

interface ResizeValue {
  width: number;
  height: number;
  name: string;
}

const RESIZE_OPTIONS: ResizeOptionProps[] = [
  {
    label: "16:9",
    icon: "landscape",
    description: "YouTube ads",
    value: {
      width: 1920,
      height: 1080,
      name: "16:9",
    },
  },
  {
    label: "9:16",
    icon: "portrait",
    description: "TikTok, YouTube Shorts",
    value: {
      width: 1080,
      height: 1920,
      name: "9:16",
    },
  },
  {
    label: "1:1",
    icon: "square",
    description: "Instagram, Facebook posts",
    value: {
      width: 1080,
      height: 1080,
      name: "1:1",
    },
  },
];

const ResizeVideo = () => {
  const handleResize = (options: ResizeValue) => {
    dispatch(DESIGN_RESIZE, {
      payload: {
        ...options,
      },
    });
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button className="border border-border/20 bg-primary/90 hover:bg-primary text-white" variant="secondary">
          Resize
        </Button>
      </PopoverTrigger>
      <PopoverContent className="z-[250] w-60 px-2.5 py-3">
        <div className="text-sm">
          {RESIZE_OPTIONS.map((option, index) => (
            <ResizeOption
              key={index}
              label={option.label}
              icon={option.icon}
              value={option.value}
              handleResize={handleResize}
              description={option.description}
            />
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
};

const ResizeOption = ({
  label,
  icon,
  value,
  description,
  handleResize,
}: ResizeOptionProps & { handleResize: (payload: ResizeValue) => void }) => {
  const Icon = Icons[icon as "text"];
  return (
    <div
      onClick={() => handleResize(value)}
      className="flex cursor-pointer items-center rounded-md p-2 hover:bg-background/20"
    >
      <div className="w-8 text-muted-foreground">
        <Icon size={20} />
      </div>
      <div>
        <div>{label}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
    </div>
  );
};
