import useLayoutStore from "../store/use-layout-store";
import { Texts } from "./texts";
import { Uploads } from "./uploads";
import { Audios } from "./audios";
import { Images } from "./images";
import { Videos } from "./videos";

const Container = ({ children }: { children: React.ReactNode }) => {
  const { showMenuItem } = useLayoutStore();
  
  if (!showMenuItem) {
    return null;
  }
  
  return (
    <div className="h-full w-full overflow-y-auto p-2">
      {children}
    </div>
  );
};

const ActiveMenuItem = () => {
  const { activeMenuItem } = useLayoutStore();

  if (activeMenuItem === "texts") {
    return <Texts />;
  }

  if (activeMenuItem === "videos") {
    return <Videos />;
  }

  if (activeMenuItem === "audios") {
    return <Audios />;
  }

  if (activeMenuItem === "images") {
    return <Images />;
  }
  if (activeMenuItem === "uploads") {
    return <Uploads />;
  }
  return null;
};

export const MenuItem = () => {
  return (
    <Container>
      <ActiveMenuItem />
    </Container>
  );
};
