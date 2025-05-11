import Timeline from "./timeline";
import useStore from "./store/use-store";
import MenuList from "./menu-list";
import { MenuItem } from "./menu-item";
import useTimelineEvents from "@/hooks/use-timeline-events";
import Scene from "./scene";
import StateManager, { DESIGN_LOAD } from "@designcombo/state";
import { ControlItem } from "./control-item";
import ControlList from "./control-list";
import { AIAssistant } from "./ai-assistant";
import { useEffect, useState } from "react";
import { dispatch } from "@designcombo/events";
import { emptyDesignWidthMagneticTrack } from "./data";
import { Button } from "@/components/ui/button";
import { Icons } from "@/components/shared/icons";
import { FileUploadDialog } from "./components/file-upload-dialog";
import { UploadsProvider, useUploadsContext } from "./context/uploads-context";
import { IImage, IVideo, IAudio } from "@designcombo/types";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import Navbar from "./navbar";
 
const stateManager = new StateManager({
  size: {
    width: 1920,
    height: 1080,
  },
  scale: {
    // 1x distance (second 0 to second 5, 5 segments).
    index: 7,
    unit: 300,
    zoom: 1 / 300,
    segments: 5,
  },
});

// Wrapper component for the upload button
const UploadButton = () => {
  const { addUploadedFiles } = useUploadsContext();
  
  const handleUpload = (files: Array<Partial<IImage | IVideo | IAudio>>) => {
    addUploadedFiles(files);
  };
  
  return (
    <FileUploadDialog 
      onUpload={handleUpload}
      trigger={
        <Button 
          variant="ghost" 
          size="icon"
          className="text-muted-foreground hover:text-foreground"
        >
          <Icons.upload width={18} />
        </Button>
      }
    />
  );
};

const EditorContent = () => {
  const { timeline, playerRef } = useStore();
  const [timelineHeight, setTimelineHeight] = useState(200);

  useTimelineEvents();

  useEffect(() => {
    if (!timeline) return;
    dispatch(DESIGN_LOAD, {
      payload: emptyDesignWidthMagneticTrack,
    });
  }, [timeline]);

  const handleTimelineResize = () => {
    const timelineContainer = document.getElementById("timeline-container");
    if (!timelineContainer) return;

    timeline?.resize(
      {
        height: timelineContainer.clientHeight - 90,
        width: timelineContainer.clientWidth - 40,
      },
      {
        force: true,
      },
    );
  };

  useEffect(() => {
    const onResize = () => handleTimelineResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [timeline]);

  // Handle timeline panel resize
  useEffect(() => {
    handleTimelineResize();
  }, [timelineHeight, timeline]);

  return (
    <div className="h-screen w-screen flex flex-col bg-gradient-to-br from-background to-background/80 text-foreground">
      {/* Include Navbar */}
      <Navbar />
      
      <ResizablePanelGroup direction="horizontal" className="flex-1 overflow-hidden mt-[72px]">
        {/* Left column - AI Assistant */}
        <ResizablePanel defaultSize={24} minSize={15} maxSize={35}>
          <div className="h-full glass-morphism border-r border-border/20">
            <AIAssistant />
          </div>
        </ResizablePanel>
        
        <ResizableHandle withHandle />
        
        {/* Center column - Video preview and timeline */}
        <ResizablePanel defaultSize={60}>
          <ResizablePanelGroup direction="vertical">
            <ResizablePanel defaultSize={75}>
              <div className="relative h-full">
                <Scene stateManager={stateManager} />
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            <ResizablePanel 
              defaultSize={25} 
              onResize={(size) => {
                const newHeight = Math.round(size * window.innerHeight / 100);
                setTimelineHeight(newHeight);
              }}
            >
              <div 
                id="timeline-container"
                className="h-full glass-morphism border-t border-border/20"
              >
                {playerRef && <Timeline stateManager={stateManager} />}
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
        
        <ResizableHandle withHandle />
        
        {/* Right column - Assets and Properties */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
          <div className="h-full glass-morphism border-l border-border/20">
            <ResizablePanelGroup direction="vertical">
              {/* Top half - Assets */}
              <ResizablePanel defaultSize={50}>
                <div className="h-full overflow-hidden">
                  <div className="h-full w-full">
                    <div className="flex h-14 items-center justify-between border-b border-border/20 px-4">
                      <h2 className="text-lg font-semibold">Assets</h2>
                      <UploadButton />
                    </div>
                    <div className="flex flex-col h-[calc(100%-56px)] w-full">
                      <MenuList />
                      <div className="flex-1 overflow-auto">
                        <MenuItem />
                      </div>
                    </div>
                  </div>
                </div>
              </ResizablePanel>
              
              <ResizableHandle withHandle />
              
              {/* Bottom half - Properties */}
              <ResizablePanel defaultSize={50}>
                <div className="h-full overflow-hidden">
                  <div className="h-full w-full">
                    <div className="flex h-14 items-center justify-between border-b border-border/20 px-4">
                      <h2 className="text-lg font-semibold">Properties</h2>
                    </div>
                    <div className="flex flex-col h-[calc(100%-56px)] w-full">
                      <ControlList />
                      <div className="flex-1 overflow-auto">
                        <ControlItem />
                      </div>
                    </div>
                  </div>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

const App = () => {
  return (
    <UploadsProvider>
      <EditorContent />
    </UploadsProvider>
  );
};

export default App;
