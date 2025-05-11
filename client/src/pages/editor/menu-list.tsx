import useLayoutStore from "./store/use-layout-store";
import { Icons } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { IMenuItem } from "@/interfaces/layout";

export default function MenuList() {
  const { setActiveMenuItem, setShowMenuItem, activeMenuItem } =
    useLayoutStore();
  
  const tabs: Array<{ id: IMenuItem; label: string; icon: React.ReactNode }> = [
    { id: "uploads", label: "All", icon: <Icons.upload width={16} /> },
    { id: "videos", label: "Video", icon: <Icons.video width={16} /> },
    { id: "audios", label: "Audio", icon: <Icons.audio width={16} /> },
    { id: "images", label: "Image", icon: <Icons.image width={16} /> },
    { id: "texts", label: "Text", icon: <Icons.type width={16} /> }
  ];
  
  return (
    <div className="w-full overflow-x-auto">
      <div className="flex min-w-max border-b">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            onClick={() => {
              setActiveMenuItem(tab.id);
              setShowMenuItem(true);
            }}
            className={cn(
              "flex items-center gap-1 px-3 py-2 rounded-none border-b-2",
              activeMenuItem === tab.id 
                ? "border-primary text-primary" 
                : "border-transparent text-muted-foreground"
            )}
            variant="ghost"
            size="sm"
          >
            {tab.icon}
            <span className="text-xs">{tab.label}</span>
          </Button>
        ))}
      </div>
    </div>
  );
}
