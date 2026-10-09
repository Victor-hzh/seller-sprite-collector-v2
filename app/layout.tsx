import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "清洁家电市场数据看板",
  description: "基于卖家精灵 Excel 的多站点、多品类亚马逊 Best Sellers 数据看板。",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}

