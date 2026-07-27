import React from "react";

import { useThemeStore } from "../../../store/themeStore";

import SidebarDefault from "./Sidebar_default";
import SidebarFuturePurple from "./Sidebar_futurePurple";
import SidebarAlexandros from "./Sidebar_alexandros";

export function Sidebar() {
  const { currentTheme } = useThemeStore();

  switch (currentTheme) {
    case "future-purple":
      return <SidebarFuturePurple />;

    case "alexandros":
      return <SidebarAlexandros />;

    default:
      return <SidebarDefault />;
  }
}