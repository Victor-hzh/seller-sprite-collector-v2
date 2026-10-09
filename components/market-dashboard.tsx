"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import {
  Activity, ArrowDown, ArrowRightLeft, ArrowUp, BadgeCheck, BarChart3,
  BookOpen, Building2, CalendarDays, ChevronDown, CircleDollarSign, Database, Download,
  ExternalLink, EyeOff, FileSpreadsheet, Filter, Gauge, History,
  Info, Layers3, PackageSearch, RotateCcw, Search,
  ShoppingCart, Sparkles, Star, Tags, TriangleAlert, Trophy, TrendingDown,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";

import dashboardJson from "@/data/dashboard-data.json";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

type Currency = { code: string; symbol: string };
type Product = {
  competitionRank?: number; sourceRank?: number | null; sources?: Array<{nodeId: string; rank: number | null; sourceUrl: string}>;
  rank: number | null; asin: string; parentAsin: string; sku: string; brand: string;
  title: string; shortTitle: string; features: string; productUrl: string; imageUrl: string;
  mainBsr: number | null; mainBsrChange: number | null; mainBsrChangeRate: number | null;
  subBsr: number | null; monthlySales: number | null; monthlySalesGrowth: number | null;
  monthlyRevenue: number | null; price: number | null; questionCount: number | null;
  reviewCount: number | null; newReviewCount: number | null; rating: number | null;
  reviewRate: number | null; fbaFee: number | null; grossMargin: number | null;
  listedDate: string; listingDays: number | null; fulfillment: string; sellerCount: number | null;
  buyboxSeller: string; sellerOrigin: string;
  badges: { bestSeller: boolean; amazonChoice: boolean; cpf: boolean; newRelease: boolean };
  content: { aPlus: boolean; video: boolean; spAds: boolean; brandStory: boolean; brandAds: boolean; deal: boolean; acKeyword: string };
  raw: Record<string, unknown>;
};
type Dataset = {
  id: string; marketplace: string; category: string; categoryLabel: string; listName: string;
  sourceUrl: string; date: string; topLimit: number; sourceFile: string; currency: Currency;
  products: Product[]; sourceUrls?: string[]; sourceCoverageComplete?: boolean; missingSourceNodes?: string[]; reviewProductCount?: number;
};
type ExpectedDataset = {
  id: string; marketplace: string; category: string; categoryLabel: string;
  listName: string; sourceUrl: string; available: boolean;
};
type DashboardPayload = {
  generatedAt: string; expectedDatasetCount: number; loadedDatasetCount: number;
  expectedDatasets: ExpectedDataset[]; datasets: Dataset[];
  exchangeRates: { base: "CNY"; date: string; source: string; sourceUrl: string; formula: string; cnyPerUnit: Record<string, number> };
  opportunityModel: { minimumMarketplaces: number; formula: string; note: string; weights: Record<string, number> };
};
type DisplayCurrency = "CNY" | "NATIVE";
type PageKey = "tracker" | "overview" | "opportunity" | "brands" | "products" | "weekly" | "guide" | "coverage";
type PriceMetric = "products" | "monthlySales" | "monthlyRevenue";
type ProductMetricFilter = "all" | "bestSeller" | "amazonChoice" | "newRelease" | "coupon" | "aPlus" | "video" | "brandStory" | "spAds" | "brandAds";
type BrandRow = {
  name: string; monthlySales: number; monthlyRevenue: number; priceTotal: number;
  priced: number; count: number; products: Product[]; averagePrice: number;
};
type BrandScatterPoint = BrandRow & { averagePriceCny: number; monthlyRevenueCny: number };
type PriceBand = { label: string; min: number; max: number };
type BrandPriceHeatmapCell = { share: number; sales: number; products: number };
type BrandPriceHeatmapRow = { brand: string; cells: BrandPriceHeatmapCell[] };
type OpportunityRow = {
  marketplace: string; marketplaceName: string; monthlyRevenueCny: number; monthlySales: number;
  averagePriceCny: number; brandCount: number; growth: number; entryFriendliness: number;
  topBrandConcentration: number; newProductShare: number;
  marketSizeScore: number; salesDemandScore: number; growthScore: number;
  friendlinessScore: number; score: number; rank: number; date: string;
};
type ProductScatterPoint = Product & {
  x: number; y: number; z: number; model: string;
};
type WeeklyRow = {
  asin: string; product: Product; previous?: Product; currentRank: number | null;
  previousRank: number | null; rankChange: number | null; revenueChange: number | null;
  revenueRate: number | null; salesChange: number | null; salesRate: number | null;
  priceChange: number | null; priceRate: number | null; rightsChanged: boolean;
  currentRights: string; previousRights: string;
};

const baseDashboardData = dashboardJson as DashboardPayload;
const japanExpectedDatasets: ExpectedDataset[] = [
  {
    id: "JP_MITE_VACUUM",
    marketplace: "JP",
    category: "Mite-Vacuum",
    categoryLabel: "除螨仪",
    listName: "布団クリーナー",
    sourceUrl: "https://www.amazon.co.jp/gp/bestsellers/kitchen/5248688051",
    available: false,
  },
  {
    id: "JP_SPOT_CLEANER",
    marketplace: "JP",
    category: "Spot-Cleaner",
    categoryLabel: "布艺清洗机",
    listName: "スチームクリーナー",
    sourceUrl: "https://www.amazon.co.jp/gp/bestsellers/kitchen/2466960051",
    available: false,
  },
  {
    id: "JP_WET_DRY_FLOOR_WASHER",
    marketplace: "JP",
    category: "Wet-Dry-Floor-Washer",
    categoryLabel: "洗地机",
    listName: "ウェットドライショップ掃除機",
    sourceUrl: "https://www.amazon.co.jp/gp/bestsellers/diy/13698381",
    available: false,
  },
  {
    id: "JP_ROBOT_VACUUM",
    marketplace: "JP",
    category: "Robot-Vacuum",
    categoryLabel: "扫地机器人",
    listName: "ロボット型クリーナー",
    sourceUrl: "https://www.amazon.co.jp/gp/bestsellers/kitchen/2353758051",
    available: false,
  },
  {
    id: "JP_STICK_VACUUM",
    marketplace: "JP",
    category: "Stick-Vacuum",
    categoryLabel: "吸尘器",
    listName: "スティッククリーナー",
    sourceUrl: "https://www.amazon.co.jp/gp/bestsellers/kitchen/13698351",
    available: false,
  },
];
const mergedExpectedDatasets = [...baseDashboardData.expectedDatasets];
for (const expected of japanExpectedDatasets) {
  if (!mergedExpectedDatasets.some((item) => item.id === expected.id)) {
    mergedExpectedDatasets.push(expected);
  }
}
const dashboardData: DashboardPayload = {
  ...baseDashboardData,
  expectedDatasetCount: mergedExpectedDatasets.length,
  expectedDatasets: mergedExpectedDatasets,
  exchangeRates: {
    ...baseDashboardData.exchangeRates,
    cnyPerUnit: {
      ...baseDashboardData.exchangeRates.cnyPerUnit,
      JPY: baseDashboardData.exchangeRates.cnyPerUnit.JPY ?? 0.042088533,
    },
  },
};
const chartColors = ["#FF610A", "#ff8c42", "#f7b32b", "#c54808", "#e04a2f", "#7d3a22", "#e98754", "#5e7480"];
const brandBubbleColors = ["#FF610A", "#ff8c42", "#f7b32b", "#c54808", "#e04a2f", "#7d3a22", "#e98754", "#d96a16", "#ef6848", "#9a3512", "#f5a623", "#c05b2e", "#ffa15a", "#a34b26", "#dc7860", "#c78a20", "#6f5960", "#5e7480"];
const marketplaceNames: Record<string, string> = { US: "美国站", UK: "英国站", DE: "德国站", FR: "法国站", IT: "意大利站", ES: "西班牙站", JP: "日本站" };
const marketplaceCurrencyCodes: Record<string, string> = { US: "USD", UK: "GBP", DE: "EUR", FR: "EUR", IT: "EUR", ES: "EUR", JP: "JPY" };
const allOverviewMarketplaces = "__ALL_MARKETPLACES__";
const topOptions = [10, 20, 30, 50];
const pageMeta: Record<PageKey, { index: string; label: string; title: string; description: string; icon: typeof Gauge }> = {
  tracker: { index: "00", label: "榜单追踪", title: "Best Sellers 榜单追踪", description: "按站点与品类查看Amazon小类榜单，支持搜索、排序、临时隐藏和自动补位。", icon: BarChart3 },
  overview: { index: "01", label: "总览", title: "市场总览", description: "快速掌握当前站点与品类的核心指标、头部品牌、头部商品和本周重点变化。", icon: Gauge },
  opportunity: { index: "02", label: "机会对比", title: "跨站点机会对比", description: "比较不同站点与品类的市场规模、需求、价格和综合进入机会。", icon: Trophy },
  brands: { index: "03", label: "品牌", title: "品牌竞争分析", description: "集中查看品牌规模、份额、价格定位与品牌明细。", icon: Building2 },
  products: { index: "04", label: "产品", title: "Top N 产品监控", description: "按竞品月销售额排名前N名监控产品销售、价格、口碑、权益和明细。", icon: PackageSearch },
  weekly: { index: "05", label: "周度异动", title: "周度异动", description: "回答本周相比上周在排名、销售、价格、进出榜和权益上发生了什么。", icon: History },
  guide: { index: "06", label: "数据指南", title: "数据指南", description: "第一次使用时，从这里了解顶部选项和各个页面是做什么的。", icon: BookOpen },
  coverage: { index: "07", label: "数据覆盖", title: "数据覆盖", description: "确认当前日期下各站点与品类的数据接入状态。", icon: Database },
};
const navigationOrder: PageKey[] = ["overview", "tracker", "opportunity", "brands", "products", "weekly", "guide"];

function compact(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
function chartLabel(value: string, maxLength = 26) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized;
}
function productModel(product: Product) {
  const sku = product.sku?.trim() ?? "";
  const labeledSku = sku.match(/^(?:style|model|modelo|set name|nombre de estilo|型号|款式)\s*:\s*(.+)$/i)?.[1]?.trim();
  if (labeledSku) return chartLabel(labeledSku, 46);

  const brand = product.brand?.trim().toLowerCase();
  const segments = (product.shortTitle || product.title)
    .split("·")
    .map((part) => part.trim())
    .filter((part) => part && part.toLowerCase() !== brand);
  const isSpecification = (value: string) => /^(?:\d+(?:[.\-]\d+)?\s*(?:mins?|min|cm|mah|aw|w|kw|kpa|pa|v|l|lbs?)|cordless vacuum cleaner|corded vacuum cleaner)$/i.test(value);
  const model = segments.find((part) => /[a-z]/i.test(part) && /\d/.test(part) && !isSpecification(part))
    ?? segments.find((part) => !isSpecification(part));
  return model ? chartLabel(model, 46) : "未识别";
}
function whole(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value);
}
function currency(value: number | null | undefined, code: string) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: code || "USD", maximumFractionDigits: Math.abs(value) < 1000 ? 2 : 0 }).format(value);
}
function generatedAtLabel(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}
function percent(value: number | null | undefined, digits = 1) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "percent", maximumFractionDigits: digits }).format(value);
}
function sum(products: Product[], key: "monthlySales" | "monthlyRevenue" | "reviewCount") {
  return products.reduce((total, product) => total + (product[key] ?? 0), 0);
}
function average(products: Product[], key: "price" | "rating") {
  const values = products.map((product) => product[key]).filter((value): value is number => value != null);
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
}
function weightedAveragePrice(products: Product[]) {
  const monthlySales = sum(products, "monthlySales");
  const monthlyRevenue = sum(products, "monthlyRevenue");
  return monthlySales > 0 && monthlyRevenue > 0 ? monthlyRevenue / monthlySales : average(products, "price");
}
function cnyRate(dataset: Dataset) { return dashboardData.exchangeRates.cnyPerUnit[dataset.currency.code] ?? 1; }
function converted(value: number | null | undefined, dataset: Dataset, display: DisplayCurrency) {
  if (value == null) return null;
  return display === "CNY" ? value * cnyRate(dataset) : value;
}
function displayMoney(value: number | null | undefined, dataset: Dataset, display: DisplayCurrency) {
  return currency(converted(value, dataset, display), display === "CNY" ? "CNY" : dataset.currency.code);
}
function productRank(product: Product) { return product.competitionRank ?? product.subBsr ?? product.rank; }
function sourceBsr(product: Product) { return product.subBsr ?? product.sourceRank ?? product.rank; }
function sameCoverage(a: Dataset, b: Dataset) { return JSON.stringify([...(a.sourceUrls ?? [a.sourceUrl])].sort()) === JSON.stringify([...(b.sourceUrls ?? [b.sourceUrl])].sort()); }
function bsrSorted(products: Product[]) {
  return [...products].sort((a, b) => (productRank(a) ?? Number.MAX_SAFE_INTEGER) - (productRank(b) ?? Number.MAX_SAFE_INTEGER));
}
function aggregate(products: Product[], key: "brand" | "buyboxSeller"): BrandRow[] {
  const rows = new Map<string, Omit<BrandRow, "averagePrice">>();
  for (const product of products) {
    const name = product[key] || "Unknown";
    const current = rows.get(name) ?? { name, monthlySales: 0, monthlyRevenue: 0, priceTotal: 0, priced: 0, count: 0, products: [] };
    current.monthlySales += product.monthlySales ?? 0;
    current.monthlyRevenue += product.monthlyRevenue ?? 0;
    if (product.price != null) { current.priceTotal += product.price; current.priced += 1; }
    current.count += 1;
    current.products.push(product);
    rows.set(name, current);
  }
  return [...rows.values()].map((row) => ({
    ...row,
    averagePrice: row.monthlySales > 0 && row.monthlyRevenue > 0
      ? row.monthlyRevenue / row.monthlySales
      : row.priced ? row.priceTotal / row.priced : 0,
  })).sort((a, b) => b.monthlySales - a.monthlySales);
}
function priceBandDefinitions(dataset: Dataset, display: DisplayCurrency): PriceBand[] {
  const symbol = display === "CNY" ? "¥" : dataset.currency.symbol;
  const bounds = display === "CNY"
    ? [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7000, Number.POSITIVE_INFINITY]
    : dataset.currency.code === "JPY"
      ? [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 70000, Number.POSITIVE_INFINITY]
      : [0, 50, 100, 150, 200, 250, 300, 350, 400, 500, Number.POSITIVE_INFINITY];
  return bounds.slice(0, -1).map((min, index) => {
    const max = bounds[index + 1];
    return { min, max, label: index === bounds.length - 2 ? `${symbol}${min}+` : `${symbol}${min}–${max - 1}` };
  });
}
function priceBands(products: Product[], dataset: Dataset, display: DisplayCurrency) {
  const multiplier = display === "CNY" ? cnyRate(dataset) : 1;
  return priceBandDefinitions(dataset, display).map((band) => {
    const matches = products.filter((product) => product.price != null && product.price * multiplier >= band.min && product.price * multiplier < band.max);
    return { name: band.label, products: matches.length, monthlySales: sum(matches, "monthlySales"), monthlyRevenue: sum(matches, "monthlyRevenue") * multiplier };
  });
}
function brandPriceHeatmap(products: Product[], dataset: Dataset, display: DisplayCurrency, limit = 5) {
  const bands = priceBandDefinitions(dataset, display);
  const totalSales = sum(products, "monthlySales");
  const brands = aggregate(products, "brand")
    .filter((brand) => brand.name && brand.name !== "Unknown")
    .slice(0, limit);
  const multiplier = display === "CNY" ? cnyRate(dataset) : 1;
  const rows: BrandPriceHeatmapRow[] = brands.map((brand) => ({
    brand: brand.name,
    cells: bands.map((band) => {
      const matches = brand.products.filter((product) => product.price != null && product.price * multiplier >= band.min && product.price * multiplier < band.max);
      const sales = sum(matches, "monthlySales");
      return { share: totalSales ? sales / totalSales : 0, sales, products: matches.length };
    }),
  }));
  const maxShare = Math.max(...rows.flatMap((row) => row.cells.map((cell) => cell.share)), 0);
  return { bands, rows, maxShare, totalSales };
}
function brandHeatCellStyle(value: number, maxValue: number): CSSProperties {
  const intensity = maxValue > 0 ? Math.sqrt(value / maxValue) : 0;
  const alpha = 0.08 + intensity * 0.88;
  return { background: `rgba(255, 97, 10, ${alpha})`, color: intensity > 0.56 ? "#fff" : "#5a2b18" };
}
function normalizeMetric(rows: OpportunityRow[], getter: (row: OpportunityRow) => number) {
  const values = rows.map(getter); const min = Math.min(...values); const max = Math.max(...values);
  return (value: number) => max === min ? 100 : ((value - min) / (max - min)) * 100;
}
function opportunityRows(category: string, date: string, includedMarkets?: Set<string>): OpportunityRow[] {
  const rows: OpportunityRow[] = dashboardData.datasets.filter((item) => item.category === category && item.date === date && (!includedMarkets || includedMarkets.has(item.marketplace))).map((item) => {
    const products = bsrSorted(item.products);
    const totalSales = sum(products, "monthlySales"); const brands = aggregate(products, "brand");
    const growthValues = products.map((product) => product.monthlySalesGrowth).filter((value): value is number => value != null);
    const growth = growthValues.length ? growthValues.reduce((total, value) => total + value, 0) / growthValues.length : 0;
    const newShare = products.length ? products.filter((product) => (product.listingDays ?? 99999) <= 365).length / products.length : 0;
    const concentration = totalSales ? (brands[0]?.monthlySales ?? 0) / totalSales : 1;
    return { marketplace: item.marketplace, marketplaceName: marketplaceNames[item.marketplace] ?? item.marketplace, monthlyRevenueCny: sum(products, "monthlyRevenue") * cnyRate(item), monthlySales: totalSales, averagePriceCny: weightedAveragePrice(products) * cnyRate(item), brandCount: brands.length, growth, entryFriendliness: (1 - concentration) * .65 + newShare * .35, topBrandConcentration: concentration, newProductShare: newShare, marketSizeScore: 0, salesDemandScore: 0, growthScore: 0, friendlinessScore: 0, score: 0, rank: 0, date: item.date };
  });
  if (!rows.length) return rows;
  const marketSize = normalizeMetric(rows, (row) => row.monthlyRevenueCny);
  const demand = normalizeMetric(rows, (row) => row.monthlySales);
  const growth = normalizeMetric(rows, (row) => row.growth);
  const friendly = normalizeMetric(rows, (row) => row.entryFriendliness);
  rows.forEach((row) => { row.marketSizeScore = marketSize(row.monthlyRevenueCny); row.salesDemandScore = demand(row.monthlySales); row.growthScore = growth(row.growth); row.friendlinessScore = friendly(row.entryFriendliness); row.score = Math.round((row.marketSizeScore * .45 + row.salesDemandScore * .25 + row.growthScore * .15 + row.friendlinessScore * .15) * 10) / 10; });
  rows.sort((a, b) => b.score - a.score); rows.forEach((row, index) => { row.rank = index + 1; }); return rows;
}
function rightsList(product?: Product) {
  if (!product) return [];
  return [product.badges.bestSeller && "Best Seller", product.badges.amazonChoice && "Amazon's Choice", product.badges.newRelease && "New Release", product.badges.cpf && "Coupon"].filter((item): item is string => Boolean(item));
}
function rightsLabel(product?: Product) {
  if (!product) return "—";
  const rights = rightsList(product);
  return rights.length ? rights.join(" · ") : "无";
}
function rightsDelta(current?: Product, previous?: Product) {
  if (!current || !previous) return "—";
  const currentRights = rightsList(current); const previousRights = rightsList(previous);
  const gained = currentRights.filter((item) => !previousRights.includes(item));
  const lost = previousRights.filter((item) => !currentRights.includes(item));
  const parts = [gained.length ? `新增 ${gained.join("、")}` : "", lost.length ? `失去 ${lost.join("、")}` : ""].filter(Boolean);
  return parts.length ? parts.join("；") : "—";
}
function weeklyRows(current: Dataset, previous?: Dataset): WeeklyRow[] {
  if (!previous || !sameCoverage(current, previous)) return [];
  const currentMap = new Map(current.products.map((product) => [product.asin, product]));
  const previousMap = new Map(previous.products.map((product) => [product.asin, product]));
  return [...new Set([...currentMap.keys(), ...previousMap.keys()])].map((asin) => {
    const currentProduct = currentMap.get(asin); const prior = previousMap.get(asin); const product = currentProduct ?? prior!;
    const currentRank = currentProduct ? productRank(currentProduct) : null; const previousRank = prior ? productRank(prior) : null;
    const rankChange = currentRank != null && previousRank != null ? previousRank - currentRank : null;
    const change = (now: number | null | undefined, before: number | null | undefined) => now != null && before != null ? now - before : null;
    const rate = (delta: number | null, before: number | null | undefined) => delta != null && before ? delta / before : null;
    const revenueChange = change(currentProduct?.monthlyRevenue, prior?.monthlyRevenue); const salesChange = change(currentProduct?.monthlySales, prior?.monthlySales); const priceChange = change(currentProduct?.price, prior?.price);
    const currentRights = rightsLabel(currentProduct); const previousRights = rightsLabel(prior);
    return { asin, product, previous: prior, currentRank, previousRank, rankChange, revenueChange, revenueRate: rate(revenueChange, prior?.monthlyRevenue), salesChange, salesRate: rate(salesChange, prior?.monthlySales), priceChange, priceRate: rate(priceChange, prior?.price), rightsChanged: Boolean(currentProduct && prior && currentRights !== previousRights), currentRights, previousRights };
  });
}
function csvCell(value: unknown) { return `"${String(value ?? "").replaceAll('"', '""')}"`; }
function downloadCsv(filename: string, headers: string[], rows: unknown[][]) {
  const body = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
  const blob = new Blob(["\ufeff", body], { type: "text/csv;charset=utf-8" }); const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}
function PanelTitle({ index, title, note, action }: { index: string; title: string; note: string; action?: ReactNode }) {
  return <div className="panel-title"><div><span>{index}</span><h2>{title}</h2></div><div className="panel-meta"><p>{note}</p>{action}</div></div>;
}
function KpiCard({ icon, tone, label, value, note }: { icon: ReactNode; tone: string; label: string; value: ReactNode; note?: ReactNode }) {
  return <article><div className={`kpi-icon ${tone}`}>{icon}</div><span>{label}</span><strong>{value}</strong>{note ? <small>{note}</small> : null}</article>;
}
function EmptyDataset({ expected }: { expected?: ExpectedDataset }) {
  const title = expected ? `${marketplaceNames[expected.marketplace] ?? expected.marketplace} · ${expected.categoryLabel}` : "这个站点与品类";
  const fileHint = expected ? `BSR_${expected.marketplace}_${expected.category}_Top50_YYYY-MM-DD.xlsx` : "对应榜单 Excel";
  return <section className="empty-dataset"><div className="empty-icon"><FileSpreadsheet /></div><h2>{title}页面已建立，等待导入数据</h2><p>榜单入口、币种和页面结构已经配置。将 <code>{fileHint}</code> 放入数据源目录并重新构建后，这个组合会自动出现在全部图表中。</p>{expected?.sourceUrl && <a href={expected.sourceUrl} target="_blank" rel="noreferrer">打开对应亚马逊榜单 <ExternalLink /></a>}</section>;
}
function OpportunityTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: OpportunityRow }> }) {
  const row = payload?.[0]?.payload; if (!active || !row) return null;
  return <div className="custom-tooltip"><strong>{row.marketplaceName}</strong><span>综合机会分 {row.score.toFixed(1)}</span><small>月销量 {whole(row.monthlySales)}</small><small>销量加权均价 {currency(row.averagePriceCny, "CNY")}</small><small>月销售额 {currency(row.monthlyRevenueCny, "CNY")}</small><small>市场规模评分 {row.marketSizeScore.toFixed(1)}</small><small>销量需求评分 {row.salesDemandScore.toFixed(1)}</small><small>增长评分 {row.growthScore.toFixed(1)}</small><small>进入友好度评分 {row.friendlinessScore.toFixed(1)}</small></div>;
}
function ProductScatterTooltip({ active, payload, currencyCode }: { active?: boolean; payload?: Array<{ payload: ProductScatterPoint }>; currencyCode: string }) {
  const product = payload?.[0]?.payload;
  if (!active || !product) return null;
  return <div className="custom-tooltip product-scatter-tooltip"><small>品牌</small><strong>{product.brand || "Unknown"}</strong><span>型号：{product.model}</span><small>价格：{currency(product.x, currencyCode)}</small><small>月销量：{whole(product.y)}</small><small>月销售额：{currency(product.z, currencyCode)}</small></div>;
}
function BrandScatterTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: BrandScatterPoint }> }) {
  const brand = payload?.[0]?.payload;
  if (!active || !brand) return null;
  return <div className="custom-tooltip product-scatter-tooltip"><small>品牌</small><strong>{brand.name}</strong><span>月销量：{whole(brand.monthlySales)}</span><small>销量加权均价：{currency(brand.averagePriceCny, "CNY")}</small><small>月销售额：{currency(brand.monthlyRevenueCny, "CNY")}</small><small>榜单商品数：{whole(brand.count)}</small></div>;
}
function brandBubbleColor(index: number) {
  return brandBubbleColors[index % brandBubbleColors.length];
}

export default function MarketDashboard() {
  const initial = dashboardData.datasets[0];
  const [activePage, setActivePage] = useState<PageKey>("overview");
  const [marketplace, setMarketplace] = useState(initial?.marketplace ?? "US");
  const [category, setCategory] = useState(initial?.category ?? "Mite-Vacuum");
  const [date, setDate] = useState(initial?.date ?? "");
  const [topN, setTopN] = useState(50);
  const [displayCurrency, setDisplayCurrency] = useState<DisplayCurrency>("NATIVE");
  const [overviewAllSites, setOverviewAllSites] = useState(false);
  const [trackerAllSites, setTrackerAllSites] = useState(false);
  const [opportunityMarkets, setOpportunityMarkets] = useState<Set<string>>(
    () => new Set(dashboardData.expectedDatasets.map((item) => item.marketplace)),
  );
  const [focusedOpportunityMarket, setFocusedOpportunityMarket] = useState("");
  const [hiddenAsins, setHiddenAsins] = useState<Set<string>>(new Set());
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const productSheetScrollY = useRef<number | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [brandSearch, setBrandSearch] = useState("");
  const [brandFilter, setBrandFilter] = useState("");
  const [brandSort, setBrandSort] = useState<"sales" | "revenue" | "price" | "share">("sales");
  const [productMetricFilter, setProductMetricFilter] = useState<ProductMetricFilter>("all");
  const [priceMetric, setPriceMetric] = useState<PriceMetric>("monthlyRevenue");
  const [showZeroMetrics, setShowZeroMetrics] = useState(false);
  const [productSort, setProductSort] = useState<"rank" | "sales" | "revenue" | "price" | "rating">("rank");
  const [trackerSearch, setTrackerSearch] = useState("");
  const [trackerSort, setTrackerSort] = useState<"rank" | "movement" | "reviews">("rank");

  useEffect(() => {
    const syncPageFromHash = () => {
      const page = window.location.hash.slice(1) as PageKey;
      if (page in pageMeta) setActivePage(page);
    };
    syncPageFromHash();
    window.addEventListener("hashchange", syncPageFromHash);
    return () => window.removeEventListener("hashchange", syncPageFromHash);
  }, []);

  useEffect(() => {
    const scrollY = productSheetScrollY.current;
    if (scrollY == null) return;
    const restoreScroll = () => window.scrollTo({ top: scrollY, left: 0, behavior: "auto" });
    restoreScroll();
    const frame = window.requestAnimationFrame(restoreScroll);
    const timer = window.setTimeout(restoreScroll, 0);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [selectedProduct]);

  const marketplaces = useMemo(
    () => [...new Set(dashboardData.expectedDatasets.map((item) => item.marketplace))],
    [],
  );
  const categoryOptions = useMemo(() => {
    const options = new Map<string, string>();
    dashboardData.expectedDatasets.forEach((item) => options.set(item.category, item.categoryLabel));
    return [...options.entries()].map(([value, label]) => ({ value, label }));
  }, []);
  const dates = useMemo(
    () => [...new Set(dashboardData.datasets.map((item) => item.date))].sort().reverse(),
    [],
  );
  const dataset = dashboardData.datasets.find(
    (item) => item.marketplace === marketplace && item.category === category && item.date === date,
  );
  const expectedSelection = dashboardData.expectedDatasets.find(
    (item) => item.marketplace === marketplace && item.category === category,
  );
  const isOverviewAllSites = activePage === "overview" && overviewAllSites;
  const isTrackerAllSites = activePage === "tracker" && trackerAllSites;
  const isCrossSiteSelection = isOverviewAllSites || isTrackerAllSites;
  const effectiveCurrency: DisplayCurrency = activePage === "opportunity" || isCrossSiteSelection ? "CNY" : displayCurrency;
  const limitedRankingMarkets = category === "Mite-Vacuum"
    ? ["US"]
    : category === "Wet-Dry-Floor-Washer"
      ? ["UK", "FR", "IT", "ES"]
      : [];
  const warningSelection = activePage === "opportunity"
    ? [...opportunityMarkets]
    : isCrossSiteSelection
      ? marketplaces
      : [marketplace];
  const affectedRankingMarkets = limitedRankingMarkets.filter((item) => warningSelection.includes(item));
  const baseProducts = dataset
    ? bsrSorted(dataset.products).filter((product) => !hiddenAsins.has(product.asin))
    : [];
  const brandData = aggregate(baseProducts, "brand");
  const totalSales = sum(baseProducts, "monthlySales");
  const previousDataset = dataset
    ? dashboardData.datasets
        .filter((item) => item.marketplace === marketplace && item.category === category && item.date < date)
        .sort((a, b) => b.date.localeCompare(a.date))[0]
    : undefined;
  const previousBaseProducts = previousDataset
    ? bsrSorted(previousDataset.products).filter((product) => !hiddenAsins.has(product.asin))
    : [];
  const changes = dataset
    ? weeklyRows({ ...dataset, products: baseProducts }, previousDataset ? { ...previousDataset, products: previousBaseProducts } : undefined)
    : [];
  const opportunities = opportunityRows(category, date, opportunityMarkets);
  const opportunityLeader = opportunities[0];

  const latestDateFor = (nextMarketplace: string, nextCategory: string) =>
    dashboardData.datasets
      .filter((item) => item.marketplace === nextMarketplace && item.category === nextCategory)
      .map((item) => item.date)
      .sort()
      .reverse()[0] ?? dates[0] ?? "";

  const latestDateForAll = (nextCategory: string) =>
    dashboardData.datasets
      .filter((item) => item.category === nextCategory)
      .map((item) => item.date)
      .sort()
      .reverse()[0] ?? dates[0] ?? "";

  const clearTemporaryFilters = () => {
    setHiddenAsins(new Set());
    setFocusedOpportunityMarket("");
    setProductSearch("");
    setBrandSearch("");
    setBrandFilter("");
    setBrandSort("sales");
    setProductMetricFilter("all");
    setShowZeroMetrics(false);
    setTrackerSearch("");
    setTrackerSort("rank");
  };
  const selectMarketplace = (value: string) => {
    setMarketplace(value);
    setDate(latestDateFor(value, category));
    setDisplayCurrency("NATIVE");
    clearTemporaryFilters();
  };
  const selectOverviewMarketplace = (value: string) => {
    if (value === allOverviewMarketplaces) {
      setOverviewAllSites(true);
      setDate(latestDateForAll(category));
      clearTemporaryFilters();
      return;
    }
    setOverviewAllSites(false);
    selectMarketplace(value);
  };
  const selectTrackerMarketplace = (value: string) => {
    if (value === allOverviewMarketplaces) {
      setTrackerAllSites(true);
      setDate(latestDateForAll(category));
      clearTemporaryFilters();
      return;
    }
    setTrackerAllSites(false);
    selectMarketplace(value);
  };
  const selectCategory = (value: string) => {
    setCategory(value);
    setDate(isCrossSiteSelection ? latestDateForAll(value) : latestDateFor(marketplace, value));
    clearTemporaryFilters();
  };
  const resetFilters = () => {
    const first = dashboardData.datasets[0];
    setMarketplace(first?.marketplace ?? marketplaces[0] ?? "US");
    setCategory(first?.category ?? categoryOptions[0]?.value ?? "");
    setDate(first?.date ?? dates[0] ?? "");
    setTopN(50);
    setDisplayCurrency("NATIVE");
    setOverviewAllSites(false);
    setTrackerAllSites(false);
    setOpportunityMarkets(new Set(marketplaces));
    setFocusedOpportunityMarket("");
    clearTemporaryFilters();
  };
  const activatePage = (page: PageKey) => {
    setActivePage(page);
    window.history.replaceState(null, "", `#${page}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openProductSheet = (product: Product) => {
    productSheetScrollY.current = window.scrollY;
    setSelectedProduct(product);
  };
  const toggleOpportunityMarket = (value: string, checked: boolean) => {
    const next = new Set(opportunityMarkets);
    if (checked) next.add(value);
    else if (next.size > 1) next.delete(value);
    setOpportunityMarkets(next);
    if (!checked && focusedOpportunityMarket === value && !next.has(value)) setFocusedOpportunityMarket("");
  };
  const hideProduct = (asin: string) => {
    setHiddenAsins((current) => new Set([...current, asin]));
  };

  const FilterBar = () => (
    <section className="filter-bar" aria-label="全局筛选器">
      <div className="filter-heading"><Filter /><div><strong>业务筛选</strong><span>所有页面同步</span></div></div>
      <label>
        <span>站点</span>
        {activePage === "opportunity" ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="multi-select-trigger">
                {opportunityMarkets.size === marketplaces.length ? "全部站点" : `已选 ${opportunityMarkets.size} 个站点`}
                <ChevronDown />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-44">
              <DropdownMenuLabel>机会对比站点</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {marketplaces.map((item) => (
                <DropdownMenuCheckboxItem
                  key={item}
                  checked={opportunityMarkets.has(item)}
                  onCheckedChange={(checked) => toggleOpportunityMarket(item, Boolean(checked))}
                  onSelect={(event) => event.preventDefault()}
                >
                  {marketplaceNames[item] ?? item}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : activePage === "overview" ? (
          <Select value={isOverviewAllSites ? allOverviewMarketplaces : marketplace} onValueChange={selectOverviewMarketplace}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={allOverviewMarketplaces}>全部站点</SelectItem>
              {marketplaces.map((item) => <SelectItem key={item} value={item}>{marketplaceNames[item] ?? item}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : activePage === "tracker" ? (
          <Select value={isTrackerAllSites ? allOverviewMarketplaces : marketplace} onValueChange={selectTrackerMarketplace}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={allOverviewMarketplaces}>全部站点</SelectItem>
              {marketplaces.map((item) => <SelectItem key={item} value={item}>{marketplaceNames[item] ?? item}</SelectItem>)}
            </SelectContent>
          </Select>
        ) : (
          <Select value={marketplace} onValueChange={selectMarketplace}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{marketplaces.map((item) => <SelectItem key={item} value={item}>{marketplaceNames[item] ?? item}</SelectItem>)}</SelectContent>
          </Select>
        )}
      </label>
      <label>
        <span>品类</span>
        <Select value={category} onValueChange={selectCategory}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{categoryOptions.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent>
        </Select>
      </label>
      <label>
        <span>数据日期</span>
        <Select value={date} onValueChange={(value) => { setDate(value); clearTemporaryFilters(); }}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{dates.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
        </Select>
      </label>
      <label>
        <span>金额单位</span>
        {activePage === "opportunity" || isCrossSiteSelection ? (
          <Button variant="outline" className="locked-select" disabled>人民币 CNY</Button>
        ) : (
          <Select value={displayCurrency} onValueChange={(value) => setDisplayCurrency(value as DisplayCurrency)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="NATIVE">站点原币 · {dataset?.currency.code ?? marketplaceCurrencyCodes[marketplace] ?? "—"}</SelectItem>
              <SelectItem value="CNY">人民币 · CNY</SelectItem>
            </SelectContent>
          </Select>
        )}
      </label>
      <div className="topn-control"><span>展示范围 · 竞品月销售额排名</span><div>{topOptions.map((item) => <button key={item} className={topN === item ? "active" : ""} onClick={() => setTopN(item)}>Top{item}</button>)}</div></div>
      <Button variant="outline" onClick={resetFilters}><RotateCcw />重置</Button>
    </section>
  );

  const DatasetBanner = () => {
    const selectedNames = [...opportunityMarkets].map((item) => marketplaceNames[item] ?? item).join("、");
    const opportunityCount = opportunities.reduce((total, row) => {
      const source = dashboardData.datasets.find((item) => item.marketplace === row.marketplace && item.category === category && item.date === date);
      return total + (source?.products.length ?? 0);
    }, 0);
    const overviewDatasets = isOverviewAllSites
      ? dashboardData.datasets.filter((item) => item.category === category && item.date === date)
      : [];
    const trackerDatasets = isTrackerAllSites
      ? dashboardData.datasets.filter((item) => item.category === category && item.date === date)
      : [];
    const overviewProductCount = overviewDatasets.reduce(
      (total, source) => total + bsrSorted(source.products).filter((product) => !hiddenAsins.has(product.asin)).length,
      0,
    );
    const trackerProductCount = trackerDatasets.reduce(
      (total, source) => total + bsrSorted(source.products).filter((product) => !hiddenAsins.has(`${source.marketplace}:${product.asin}`)).length,
      0,
    );
    const categoryLabel = dataset?.categoryLabel ?? overviewDatasets[0]?.categoryLabel ?? trackerDatasets[0]?.categoryLabel ?? expectedSelection?.categoryLabel ?? category;
    const bannerTitle = activePage === "opportunity"
      ? `${selectedNames} · ${categoryLabel}`
      : isTrackerAllSites
        ? `全部站点 · ${categoryLabel}`
        : isOverviewAllSites
        ? `全部站点 · ${categoryLabel}`
        : `${marketplaceNames[marketplace] ?? marketplace} · ${categoryLabel}`;
    const productCount = activePage === "opportunity"
      ? opportunityCount
      : isTrackerAllSites
        ? trackerProductCount
        : isOverviewAllSites
        ? overviewProductCount
        : baseProducts.length;
    return (
      <section className="dataset-banner">
        <div><span className="live-dot" /><span><strong>{bannerTitle}</strong><p>全部清洗竞品统计{dataset?.reviewProductCount ? ` · ${dataset.reviewProductCount} 个待确认，未计入` : ''}</p></span></div>
        <div><CalendarDays /><span>{date}<small>数据日期</small></span></div>
        <div><Database /><span>{productCount}<small>有效 ASIN</small></span></div>
        <div className="fx-inline"><ArrowRightLeft /><span>{effectiveCurrency === "CNY" ? "统一人民币" : `${dataset?.currency.code ?? marketplaceCurrencyCodes[marketplace] ?? "—"} 原币`}<small>{effectiveCurrency === "CNY" ? `汇率日 ${dashboardData.exchangeRates.date}` : "站点口径"}</small></span></div>
        {!isCrossSiteSelection && dataset?.sourceUrl && (dataset.sourceUrls ?? [dataset.sourceUrl]).map((url, index) => <a key={url} href={url} target="_blank" rel="noreferrer">来源榜单 {index + 1} <ExternalLink /></a>)}
      </section>
    );
  };

  const PageHeading = () => {
    const meta = pageMeta[activePage];
    return <section className="page-heading"><span className="page-index">{meta.index}</span><div><p>{meta.label.toUpperCase()}</p><h2>{meta.title}</h2><span>{meta.description}</span></div></section>;
  };

  const RankingAvailabilityWarning = () => {
    if (!affectedRankingMarkets.length) return null;
    const affectedLabels = affectedRankingMarkets.map((item) => marketplaceNames[item] ?? item).join("、");
    const categoryLabel = categoryOptions.find((item) => item.value === category)?.label ?? category;
    return (
      <div className="ranking-warning-wrap">
        <section className="ranking-warning" role="status" aria-live="polite">
          <TriangleAlert />
          <div>
            <strong>细分榜单数据可能不完整</strong>
            <p><b>{affectedLabels} · {categoryLabel}</b>受亚马逊类目与榜单结构限制，目前无法获得准确的对应细分 Best Sellers 榜单。页面继续展示现有来源数据，但可能存在商品缺失，排名及市场规模请仅作参考。</p>
          </div>
        </section>
      </div>
    );
  };

  const TrackerPage = () => {
    const trackerDatasets = isTrackerAllSites
      ? dashboardData.datasets.filter((item) => item.category === category && item.date === date)
      : dataset ? [dataset] : [];
    if (!trackerDatasets.length) return <EmptyDataset expected={expectedSelection} />;

    const allEntries = trackerDatasets.flatMap((source) => {
      const hiddenKey = (product: Product) => isTrackerAllSites ? `${source.marketplace}:${product.asin}` : product.asin;
      const currentProducts = bsrSorted(source.products)
        .filter((product) => !hiddenAsins.has(hiddenKey(product))).slice(0, topN)
        ;
      const priorSource = dashboardData.datasets
        .filter((item) => item.marketplace === source.marketplace && item.category === category && item.date < date)
        .sort((a, b) => b.date.localeCompare(a.date))[0];
      const priorProducts = priorSource
        ? bsrSorted(priorSource.products).filter((product) => !hiddenAsins.has(hiddenKey(product)))
        : [];
      const sourceChanges = weeklyRows(
        { ...source, products: currentProducts },
        priorSource ? { ...priorSource, products: priorProducts } : undefined,
      );
      const movementByAsin = new Map(sourceChanges.map((item) => [item.asin, item]));
      return currentProducts.map((product) => ({
        key: `${source.marketplace}:${product.asin}`,
        source,
        product,
        movement: movementByAsin.get(product.asin),
        previousDataset: priorSource,
        revenueCny: converted(product.monthlyRevenue, source, "CNY"),
        priceCny: converted(product.price, source, "CNY"),
      }));
    });
    const visibleEntries = allEntries;
    const rankedEntries = [...visibleEntries].sort((a, b) => isTrackerAllSites
      ? (b.revenueCny ?? -1) - (a.revenueCny ?? -1)
        || (b.product.monthlySales ?? 0) - (a.product.monthlySales ?? 0)
        || a.source.marketplace.localeCompare(b.source.marketplace)
        || (productRank(a.product) ?? 9999) - (productRank(b.product) ?? 9999)
      : (productRank(a.product) ?? 9999) - (productRank(b.product) ?? 9999));
    const filteredRankByKey = new Map(rankedEntries.map((entry, index) => [entry.key, index + 1]));
    const search = trackerSearch.trim().toLowerCase();
    const trackerEntries = rankedEntries
      .filter(({ product, source }) => !search || [product.asin, product.brand, product.shortTitle, product.title, marketplaceNames[source.marketplace], source.marketplace].some((value) => value?.toLowerCase().includes(search)))
      .sort((a, b) => {
        if (isTrackerAllSites) return 0;
        if (trackerSort === "movement") return (b.movement?.rankChange ?? 0) - (a.movement?.rankChange ?? 0);
        if (trackerSort === "reviews") return (b.product.reviewCount ?? 0) - (a.product.reviewCount ?? 0);
        return (productRank(a.product) ?? 9999) - (productRank(b.product) ?? 9999);
      });
    const biggestMover = [...visibleEntries]
      .map((entry) => ({ entry, change: entry.movement?.rankChange ?? 0 }))
      .sort((a, b) => b.change - a.change)[0];
    const previousDates = new Set(visibleEntries.map((entry) => entry.previousDataset?.date).filter((value): value is string => Boolean(value)));
    const Movement = ({ entry }: { entry: (typeof allEntries)[number] }) => {
      if (!entry.previousDataset) return <span className="rank-flat">—</span>;
      const row = entry.movement;
      if (!row || row.previousRank == null) return <span className="rank-new">NEW</span>;
      if ((row.rankChange ?? 0) > 0) return <span className="rank-up">↑ {row.rankChange}</span>;
      if ((row.rankChange ?? 0) < 0) return <span className="rank-down">↓ {Math.abs(row.rankChange ?? 0)}</span>;
      return <span className="rank-flat">0</span>;
    };
    const categoryLabel = trackerDatasets[0].categoryLabel;
    const trackerTitle = isTrackerAllSites ? `全部站点 · ${categoryLabel}月销售额排名` : `清洗竞品 Top ${topN}`;
    const trackerNote = isTrackerAllSites
      ? `${trackerEntries.length} 条结果 · 各站点 Top${topN} 合并 · 按人民币月销售额由高到低`
      : `${trackerEntries.length} 条结果 · 隐藏商品刷新或切换筛选后恢复`;

    return <>
      <section className="kpi-grid tracker-kpis">
        <KpiCard icon={<Layers3 />} tone="green" label={isTrackerAllSites ? "覆盖站点" : "监测榜单"} value={isTrackerAllSites ? trackerDatasets.length : dashboardData.loadedDatasetCount} />
        <KpiCard icon={<PackageSearch />} tone="gold" label="当前展示" value={trackerEntries.length} note={isTrackerAllSites ? `${trackerDatasets.length} 站点 · 各站点 Top${topN}` : `Top${topN} · 隐藏 ${hiddenAsins.size} 个`} />
        <KpiCard icon={<ArrowUp />} tone="blue" label="最大上升" value={biggestMover?.change && biggestMover.change > 0 ? `+${biggestMover.change}` : "—"} note={biggestMover?.change && biggestMover.change > 0 ? `${isTrackerAllSites ? `${marketplaceNames[biggestMover.entry.source.marketplace] ?? biggestMover.entry.source.marketplace} · ` : ""}${biggestMover.entry.product.brand || "Unknown"}` : previousDates.size ? "本期暂无上升" : "等待下一期数据"} />
        <KpiCard icon={<CalendarDays />} tone="violet" label="数据日期" value={date} note={previousDates.size ? isTrackerAllSites ? "对比各站点上一期" : `对比 ${[...previousDates][0]}` : "当前最新一期"} />
      </section>

      <section className="tracker-source-note">
        <Database />
        <div><strong>已接入市场雷达统一数据源</strong><span>以后只需更新这一套SellerSprite数据包，榜单追踪与其他业务页面会同步更新。</span></div>
        <Badge variant="outline">{isTrackerAllSites ? "全部站点" : marketplaceNames[marketplace] ?? marketplace} · {categoryLabel}</Badge>
      </section>

      <section className="product-panel tracker-panel">
        <PanelTitle index="01" title={trackerTitle} note={trackerNote} />
        <div className="table-toolbar tracker-tools">
          <label className="search-box"><Search /><input value={trackerSearch} onChange={(event) => setTrackerSearch(event.target.value)} placeholder={isTrackerAllSites ? "搜索商品、品牌、ASIN 或站点" : "搜索商品、品牌或 ASIN"} /></label>
          {isTrackerAllSites ? (
            <Button variant="outline" className="tracker-revenue-sort" disabled>月销售额 ↓ · 人民币</Button>
          ) : (
            <Select value={trackerSort} onValueChange={(value) => setTrackerSort(value as typeof trackerSort)}>
              <SelectTrigger className="tracker-sort"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="rank">按排名</SelectItem><SelectItem value="movement">按涨幅</SelectItem><SelectItem value="reviews">按评价数</SelectItem></SelectContent>
            </Select>
          )}
          {hiddenAsins.size > 0 && <button className="link-button" onClick={() => setHiddenAsins(new Set())}>恢复隐藏（{hiddenAsins.size}）</button>}
          {!isTrackerAllSites && dataset?.sourceUrl && <a className="tracker-source-link" href={dataset.sourceUrl} target="_blank" rel="noreferrer">查看Amazon原始榜单 <ExternalLink /></a>}
        </div>
        <div className="product-table-wrap tracker-table tracker-desktop">
          <Table>
            <TableHeader><TableRow><TableHead>{isTrackerAllSites ? "月销额排名" : "筛选后排名"}</TableHead>{isTrackerAllSites && <TableHead>站点 / 原BSR</TableHead>}<TableHead>商品</TableHead><TableHead>变化</TableHead><TableHead>{isTrackerAllSites ? "价格（人民币）" : "价格"}</TableHead>{isTrackerAllSites && <TableHead>月销售额（人民币）</TableHead>}<TableHead>评分</TableHead><TableHead>评价数</TableHead><TableHead>操作</TableHead></TableRow></TableHeader>
            <TableBody>{trackerEntries.map((entry) => { const { product, source } = entry; return <TableRow key={entry.key} className="clickable-row" onClick={() => openProductSheet(product)}>
              <TableCell><div className="tracker-rank"><strong>{filteredRankByKey.get(entry.key) ?? "—"}</strong>{!isTrackerAllSites && <small>来源 BSR #{sourceBsr(product) ?? "—"}</small>}</div></TableCell>
              {isTrackerAllSites && <TableCell><div className="tracker-site"><strong>{marketplaceNames[source.marketplace] ?? source.marketplace}</strong><small>来源 BSR #{sourceBsr(product) ?? "—"}</small></div></TableCell>}
              <TableCell><div className="tracker-product">{product.imageUrl ? <img src={product.imageUrl} alt="" /> : <span className="image-placeholder"><PackageSearch /></span>}<span><strong>{product.shortTitle || product.title}</strong><small>{product.brand || "Unknown"} · {product.asin}</small></span></div></TableCell>
              <TableCell><Movement entry={entry} /></TableCell>
              <TableCell className="numeric"><strong>{isTrackerAllSites ? currency(entry.priceCny, "CNY") : displayMoney(product.price, source, effectiveCurrency)}</strong></TableCell>
              {isTrackerAllSites && <TableCell className="numeric tracker-revenue"><strong>{currency(entry.revenueCny, "CNY")}</strong></TableCell>}
              <TableCell><div className="rating-cell"><Star />{product.rating ?? "—"}</div></TableCell>
              <TableCell className="numeric">{whole(product.reviewCount)}</TableCell>
              <TableCell><div className="row-actions"><Button size="icon" variant="ghost" title="打开商品详情" onClick={(event) => { event.stopPropagation(); openProductSheet(product); }}><PackageSearch /></Button><Button size="icon" variant="ghost" title="本次查看中隐藏" onClick={(event) => { event.stopPropagation(); hideProduct(isTrackerAllSites ? entry.key : product.asin); }}><EyeOff /></Button>{product.productUrl && <Button size="icon" variant="ghost" asChild><a href={product.productUrl} target="_blank" rel="noreferrer" title="打开Amazon商品页" onClick={(event) => event.stopPropagation()}><ExternalLink /></a></Button>}</div></TableCell>
            </TableRow>; })}</TableBody>
          </Table>
        </div>
        <div className="tracker-mobile-list">{trackerEntries.map((entry) => { const { product, source } = entry; return <article key={entry.key}>
          <button className="tracker-mobile-main" onClick={() => openProductSheet(product)}>{product.imageUrl ? <img src={product.imageUrl} alt="" /> : <span className="image-placeholder"><PackageSearch /></span>}<span><strong>{filteredRankByKey.get(entry.key) ?? "—"}. {product.shortTitle || product.title}</strong><small>{isTrackerAllSites ? `${marketplaceNames[source.marketplace] ?? source.marketplace} · 来源 BSR #${sourceBsr(product) ?? "—"} · ${product.brand || "Unknown"}` : `${product.brand || "Unknown"} · ${displayMoney(product.price, source, effectiveCurrency)}`}</small><em>{isTrackerAllSites ? `月销额 ${currency(entry.revenueCny, "CNY")} · 价格 ${currency(entry.priceCny, "CNY")}` : null}{isTrackerAllSites ? " · " : null}<Movement entry={entry} /> · ★ {product.rating ?? "—"} · {whole(product.reviewCount)} 评</em></span></button>
          <Button size="icon" variant="ghost" title="本次查看中隐藏" onClick={() => hideProduct(isTrackerAllSites ? entry.key : product.asin)}><EyeOff /></Button>
        </article>; })}</div>
      </section>
    </>;
  };

  const OverviewPage = () => {
    const overviewDatasets = isOverviewAllSites
      ? dashboardData.datasets.filter((item) => item.category === category && item.date === date)
      : dataset ? [dataset] : [];
    if (!overviewDatasets.length) return <EmptyDataset expected={expectedSelection} />;

    const overviewEntries = overviewDatasets.flatMap((source) =>
      bsrSorted(source.products)
        .filter((product) => !hiddenAsins.has(product.asin))
        
        .map((product, index) => ({
          source,
          product,
          listPosition: index + 1,
          normalized: isOverviewAllSites
            ? {
                ...product,
                monthlyRevenue: converted(product.monthlyRevenue, source, "CNY"),
                price: converted(product.price, source, "CNY"),
                fbaFee: converted(product.fbaFee, source, "CNY"),
              }
            : product,
        })),
    );
    const overviewProducts = overviewEntries.map((item) => item.normalized);
    const overviewBrandData = aggregate(overviewProducts, "brand");
    const overviewTotalSales = sum(overviewProducts, "monthlySales");
    const overviewTotalRevenue = sum(overviewProducts, "monthlyRevenue");
    const overviewTop20Revenue = overviewEntries
      .filter((item) => item.listPosition <= 20)
      .reduce((total, item) => total + (item.normalized.monthlyRevenue ?? 0), 0);
    const overviewMoney = (value: number | null | undefined) => isOverviewAllSites
      ? currency(value, "CNY")
      : displayMoney(value, overviewDatasets[0], effectiveCurrency);
    const brandRevenue = [...overviewBrandData].sort((a, b) => b.monthlyRevenue - a.monthlyRevenue).slice(0, 5);
    const productRevenue = [...overviewEntries]
      .sort((a, b) => (b.normalized.monthlyRevenue ?? 0) - (a.normalized.monthlyRevenue ?? 0))
      .slice(0, 10)
      .map((item) => ({
        ...item.normalized,
        product: item.product,
        name: `${isOverviewAllSites ? `${marketplaceNames[item.source.marketplace] ?? item.source.marketplace} · ` : ""}${item.normalized.shortTitle || item.normalized.title}`,
      }));
    const validPriceCount = overviewProducts.filter((item) => item.price != null).length;
    const previousByMarketplace = new Map<string, Dataset>();
    overviewDatasets.forEach((source) => {
      const previous = dashboardData.datasets
        .filter((item) => item.marketplace === source.marketplace && item.category === category && item.date < date)
        .sort((a, b) => b.date.localeCompare(a.date))[0];
      if (previous) previousByMarketplace.set(source.marketplace, previous);
    });
    const previousEntries = [...previousByMarketplace.values()].flatMap((source) =>
      bsrSorted(source.products)
        .filter((product) => !hiddenAsins.has(product.asin))
        
        .map((product) => isOverviewAllSites
          ? {
              ...product,
              monthlyRevenue: converted(product.monthlyRevenue, source, "CNY"),
              price: converted(product.price, source, "CNY"),
              fbaFee: converted(product.fbaFee, source, "CNY"),
            }
          : product),
    );
    const previousSales = sum(previousEntries, "monthlySales");
    const previousRevenue = sum(previousEntries, "monthlyRevenue");
    const hasCompleteHistory = previousByMarketplace.size === overviewDatasets.length && overviewDatasets.every((source) => sameCoverage(source, previousByMarketplace.get(source.marketplace)!));
    const changeRate = (current: number, previous: number) => hasCompleteHistory && previous ? (current - previous) / previous : null;
    const salesRate = changeRate(overviewTotalSales, previousSales);
    const revenueRate = changeRate(overviewTotalRevenue, previousRevenue);
    const top5Concentration = overviewTotalRevenue
      ? brandRevenue.reduce((value, item) => value + item.monthlyRevenue, 0) / overviewTotalRevenue
      : 0;
    const rights = [
      { label: "Best Seller", value: overviewProducts.filter((item) => item.badges.bestSeller).length },
      { label: "Amazon's Choice", value: overviewProducts.filter((item) => item.badges.amazonChoice).length },
      { label: "New Release", value: overviewProducts.filter((item) => item.badges.newRelease).length },
      { label: "优惠券权益", value: overviewProducts.filter((item) => item.badges.cpf).length },
    ];
    const overviewChanges = overviewDatasets.flatMap((source) => {
      const previous = previousByMarketplace.get(source.marketplace);
      const currentProducts = bsrSorted(source.products).filter((product) => !hiddenAsins.has(product.asin));
      const priorProducts = previous
        ? bsrSorted(previous.products).filter((product) => !hiddenAsins.has(product.asin))
        : [];
      return previous ? weeklyRows({ ...source, products: currentProducts }, { ...previous, products: priorProducts }) : [];
    });
    const rankedChanges = overviewChanges.filter((item) => item.rankChange != null);
    const biggestRise = [...rankedChanges].filter((item) => (item.rankChange ?? 0) > 0).sort((a, b) => (b.rankChange ?? 0) - (a.rankChange ?? 0))[0];
    const biggestFall = [...rankedChanges].filter((item) => (item.rankChange ?? 0) < 0).sort((a, b) => (a.rankChange ?? 0) - (b.rankChange ?? 0))[0];
    const enteredTop20 = overviewChanges.find((item) => (item.currentRank ?? 999) <= 20 && (item.previousRank == null || item.previousRank > 20));
    const exitedTop20 = overviewChanges.find((item) => (item.previousRank ?? 999) <= 20 && (item.currentRank == null || item.currentRank > 20));
    const previousDates = [...new Set([...previousByMarketplace.values()].map((item) => item.date))];
    const previousLabel = hasCompleteHistory
      ? previousDates.length === 1 ? `对比 ${previousDates[0]}` : "对比各站点上一期"
      : isOverviewAllSites ? "等待全部站点上一期数据" : "等待第二个数据日期";
    const trendText = (value: number | null) => value == null
      ? <span>暂无上期数据</span>
      : <span className={value >= 0 ? "positive" : "negative"}>环比 {value >= 0 ? "+" : ""}{percent(value)}</span>;
    const highlightName = (row?: WeeklyRow) => row?.product.shortTitle || row?.product.title || "本期无变化";
    return <>
      <section className="kpi-grid">
        <KpiCard icon={<ShoppingCart />} tone="green" label="月销量" value={whole(overviewTotalSales)} note={<>{`${isOverviewAllSites ? `${overviewDatasets.length}个站点 · ` : ""}全部有效竞品合计 · `}{trendText(salesRate)}</>} />
        <KpiCard icon={<CircleDollarSign />} tone="gold" label="月销售额" value={overviewMoney(overviewTotalRevenue)} note={<>{`${isOverviewAllSites ? "人民币 CNY" : effectiveCurrency === "CNY" ? "CNY" : overviewDatasets[0].currency.code}口径 · `}{trendText(revenueRate)}</>} />
        <KpiCard icon={<Tags />} tone="blue" label="销量加权均价" value={overviewMoney(weightedAveragePrice(overviewProducts))} note={`${validPriceCount} 个有效价格样本 · 月销售额 ÷ 月销量`} />
        <KpiCard icon={<PackageSearch />} tone="violet" label="有效商品" value={whole(overviewProducts.length)} note={`${overviewProducts.filter((item) => item.asin).length} 个有效ASIN · 全部清洗竞品`} />
        <KpiCard icon={<Building2 />} tone="coral" label="品牌数量" value={whole(overviewBrandData.length)} note={`Top5品牌销售额集中度 ${percent(top5Concentration)}`} />
        <KpiCard icon={<Layers3 />} tone="slate" label="Top20销售额占比" value={percent(overviewTotalRevenue ? overviewTop20Revenue / overviewTotalRevenue : 0)} note="按完整清洗竞品池计算" />
      </section>
      <section className="analysis-grid two-column overview-primary-charts">
        <article className="chart-panel"><PanelTitle index="01" title="品牌月销售额 Top5" note="当前Top5品牌" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={brandRevenue} layout="vertical" margin={{ left: 8, right: 32 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={compact} /><YAxis type="category" dataKey="name" width={95} tick={{ fontSize: 9 }} /><Tooltip formatter={(value) => overviewMoney(Number(value))} /><Bar dataKey="monthlyRevenue" fill="#FF610A" radius={[0, 3, 3, 0]} /></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel clickable-chart product-revenue-chart"><PanelTitle index="02" title="商品月销售额 Top10" note="点击商品打开完整详情" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={productRevenue} layout="vertical" margin={{ top: 8, left: 10, right: 32, bottom: 4 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={compact} /><YAxis type="category" dataKey="name" width={165} interval={0} tickLine={false} tick={{ fontSize: 10, fill: "#6c5d55" }} tickFormatter={(value) => chartLabel(String(value))} /><Tooltip formatter={(value) => overviewMoney(Number(value))} /><Bar dataKey="monthlyRevenue" barSize={16} fill="#c54808" radius={[0, 3, 3, 0]} onClick={(entry) => { const product = entry?.payload?.product as Product | undefined; if (product) setSelectedProduct(product); }} /></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel wide"><PanelTitle index="03" title="榜单权益摘要" note="当前Top N商品覆盖" /><div className="rights-summary-grid overview-rights">{rights.map((item) => <div key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{percent(overviewProducts.length ? item.value / overviewProducts.length : 0)}</small></div>)}</div></article>
      </section>
      <section className="overview-weekly-panel">
        <PanelTitle index="04" title="本周重点变化" note={previousLabel} />
        <div className="weekly-highlight-grid">{previousByMarketplace.size ? <>
          <button type="button" disabled={!biggestRise} onClick={() => biggestRise && openProductSheet(biggestRise.product)}><ArrowUp /><span>排名上升最快</span><strong className="highlight-product">{highlightName(biggestRise)}</strong><small>{biggestRise ? `上升 ${biggestRise.rankChange} 名 · 点击查看详情` : "本期无上升"}</small></button>
          <button type="button" disabled={!biggestFall} onClick={() => biggestFall && openProductSheet(biggestFall.product)}><ArrowDown /><span>排名下降最快</span><strong className="highlight-product">{highlightName(biggestFall)}</strong><small>{biggestFall ? `下降 ${Math.abs(biggestFall.rankChange ?? 0)} 名 · 点击查看详情` : "本期无下降"}</small></button>
          <button type="button" disabled={!enteredTop20} onClick={() => enteredTop20 && openProductSheet(enteredTop20.product)}><Sparkles /><span>新进入Top20</span><strong className="highlight-product">{highlightName(enteredTop20)}</strong><small>{enteredTop20 ? `当前第 ${enteredTop20.currentRank ?? "—"} 名 · 点击查看详情` : "本期无新进榜"}</small></button>
          <button type="button" disabled={!exitedTop20} onClick={() => exitedTop20 && openProductSheet(exitedTop20.product)}><TrendingDown /><span>退出Top20</span><strong className="highlight-product">{highlightName(exitedTop20)}</strong><small>{exitedTop20 ? `上期第 ${exitedTop20.previousRank ?? "—"} 名 · 点击查看详情` : "本期无出榜"}</small></button>
        </> : <div className="no-history"><History /><strong>暂无周度排名变动结果</strong><span>当前没有上一期同站点、同品类数据；下周导入后自动生成上升、下降、进榜与出榜四项结果。</span></div>}</div>
      </section>
    </>;
  };

  const OpportunityPage = () => {
    const selectedDatasets = dashboardData.datasets.filter((item) => item.category === category && item.date === date && opportunityMarkets.has(item.marketplace));
    const selectedMarkets = marketplaces.filter((item) => opportunityMarkets.has(item));
    const allCategories = categoryOptions.map((item) => item.value);
    const heatValues = selectedMarkets.flatMap((market) => allCategories.map((cat) => {
      const item = dashboardData.datasets.find((source) => source.marketplace === market && source.category === cat && source.date === date);
      return { marketplace: market, category: cat, value: item ? sum(bsrSorted(item.products), "monthlyRevenue") * cnyRate(item) : 0 };
    }));
    const maxHeat = Math.max(...heatValues.map((item) => item.value), 1);
    const heatCellStyle = (value: number) => {
      const intensity = value > 0 ? Math.sqrt(value / maxHeat) : 0;
      const opacity = value > 0 ? .18 + intensity * .82 : .06;
      return {
        backgroundColor: `rgba(255,97,10,${opacity.toFixed(3)})`,
        color: intensity > .52 ? "#fff" : "#8f3200",
      };
    };
    const opportunityFocus = opportunities.find((item) => item.marketplace === focusedOpportunityMarket);
    const selectedOpportunity = opportunityFocus ?? opportunityLeader;
    const focusLabel = opportunityFocus ? `当前聚焦：${opportunityFocus.marketplaceName}` : "点击右侧站点查看详细评分";
    const opportunityScoreItems = selectedOpportunity ? [
      {
        label: "市场规模",
        score: selectedOpportunity.marketSizeScore,
        basis: `月销售额 ${currency(selectedOpportunity.monthlyRevenueCny, "CNY")}`,
      },
      {
        label: "销量需求",
        score: selectedOpportunity.salesDemandScore,
        basis: `月销量 ${whole(selectedOpportunity.monthlySales)}`,
      },
      {
        label: "增长",
        score: selectedOpportunity.growthScore,
        basis: `Top${topN}商品月销量增长率均值 ${percent(selectedOpportunity.growth)}`,
      },
      {
        label: "进入友好度",
        score: selectedOpportunity.friendlinessScore,
        basis: `头部品牌集中度 ${percent(selectedOpportunity.topBrandConcentration)} · 一年内新品占比 ${percent(selectedOpportunity.newProductShare)}`,
      },
    ] : [];
    return <>
      <section className="opportunity-panel">
        <div className="opportunity-body">
          <div className="opportunity-lead">
            <div className="opportunity-lead-heading"><div className="opportunity-icon"><Trophy /></div><div><span>{opportunityFocus ? "当前聚焦站点" : "当前综合机会领先站点"}</span><strong>{selectedOpportunity?.marketplaceName ?? "暂无可比数据"}</strong><p>{selectedOpportunity ? `综合机会分 ${selectedOpportunity.score.toFixed(1)} · 第 ${selectedOpportunity.rank}/${opportunities.length} 名 · ${categoryOptions.find((item) => item.value === category)?.label}` : "请至少保留一个已接入站点"}</p></div></div>
            {selectedOpportunity && <>
              <div className="score-basis"><strong>得分依据</strong>{opportunityScoreItems.map((item) => <div key={item.label}><span>{item.label}</span><em>{item.score.toFixed(1)} 分</em><p>{item.basis}</p></div>)}<small>右侧为原始数据，黄色数字为该指标在当前所选站点中的相对得分。系统按站点间的高低区间线性换算：该项表现最高的站点记 100 分，最低记 0 分，其余按所处位置折算。进入友好度原始值＝品牌分散度 × 65%＋一年内新品占比 × 35%；最终综合机会分＝市场规模得分 × 45%＋销量需求得分 × 25%＋增长得分 × 15%＋进入友好度得分 × 15%。</small></div>
            </>}
          </div>
          <div className="opportunity-visual"><ResponsiveContainer width="100%" height={420}><BarChart data={opportunities} layout="vertical" margin={{ left: 12, right: 32 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" domain={[0, 100]} /><YAxis type="category" dataKey="marketplaceName" width={80} /><Tooltip content={<OpportunityTooltip />} /><Bar dataKey="score" radius={[0, 4, 4, 0]} onClick={(entry) => setFocusedOpportunityMarket(String(entry?.payload?.marketplace ?? ""))}>{opportunities.map((row, index) => <Cell key={row.marketplace} fill={focusedOpportunityMarket ? (row.marketplace === focusedOpportunityMarket ? "#f7b32b" : "#d5b4a2") : chartColors[index % chartColors.length]} />)}</Bar></BarChart></ResponsiveContainer><div className="opportunity-focus-hint">{focusLabel}</div></div>
        </div>
        <div className="opportunity-foot"><Sparkles /><span>综合机会分只用于站点横向比较，不等同于实际市场份额或销售预测；所有金额统一折算为人民币。</span><span>{dashboardData.opportunityModel.formula}</span></div>
      </section>
      <section className="analysis-grid two-column">
        {[
          { index: "01", title: "月销售额规模", key: "monthlyRevenueCny" as const, color: "#FF610A", formatter: (value: number) => currency(value, "CNY") },
          { index: "02", title: "月销量需求", key: "monthlySales" as const, color: "#c54808", formatter: whole },
          { index: "03", title: "销量加权均价", key: "averagePriceCny" as const, color: "#f7b32b", formatter: (value: number) => currency(value, "CNY") },
          { index: "04", title: "品牌数量", key: "brandCount" as const, color: "#e04a2f", formatter: whole },
        ].map((metric) => {
          const chartRows = [...opportunities].sort((left, right) => Number(right[metric.key]) - Number(left[metric.key]));
          return <article className="chart-panel" key={metric.key}><PanelTitle index={metric.index} title={metric.title} note={focusLabel} /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartRows}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="marketplaceName" /><YAxis tickFormatter={compact} /><Tooltip formatter={(value) => metric.formatter(Number(value))} /><Bar dataKey={metric.key} radius={[3, 3, 0, 0]} onClick={(entry) => setFocusedOpportunityMarket(String(entry?.payload?.marketplace ?? ""))}>{chartRows.map((row) => <Cell key={row.marketplace} fill={focusedOpportunityMarket ? (row.marketplace === focusedOpportunityMarket ? "#f7b32b" : "#dfc2b2") : metric.color} />)}</Bar></BarChart></ResponsiveContainer></div></article>;
        })}
      </section>
      <section className="analysis-grid opportunity-matrix-grid">
        <article className="chart-panel heatmap-panel">
          <PanelTitle index="05" title="站点 × 品类月销售额热力图" note={`${selectedMarkets.length} 个站点 × ${categoryOptions.length} 个品类 · 月销售额（人民币）`} />
          <div className="heatmap">
            <div className="heatmap-guide"><span>颜色越深，月销售额越高</span><div><small>低</small><i /><small>高</small></div><p>色阶已压缩极端值，具体金额以格内数字为准；金色标记当前品类与聚焦站点。</p></div>
            <div className="heatmap-head" style={{ gridTemplateColumns: `150px repeat(${selectedMarkets.length}, minmax(130px, 1fr))` }}><span>品类</span>{selectedMarkets.map((market) => <strong key={market} className={focusedOpportunityMarket === market ? "focused" : ""}>{marketplaceNames[market] ?? market}</strong>)}</div>
            {categoryOptions.map((cat) => <div className={`heatmap-row ${cat.value === category ? "selected-category" : ""}`} key={cat.value} style={{ gridTemplateColumns: `150px repeat(${selectedMarkets.length}, minmax(130px, 1fr))` }}><strong>{cat.label}</strong>{selectedMarkets.map((market) => { const cell = heatValues.find((item) => item.marketplace === market && item.category === cat.value); const value = cell?.value ?? 0; return <span key={market} className={focusedOpportunityMarket === market ? "focused" : ""} style={heatCellStyle(value)} title={`${marketplaceNames[market] ?? market} · ${cat.label}：${currency(value, "CNY")}`}>{compact(value)}</span>; })}</div>)}
          </div>
        </article>
      </section>
      {selectedDatasets.length === 0 && <EmptyDataset expected={expectedSelection} />}
    </>;
  };

  const BrandsPage = () => {
    if (!dataset) return <EmptyDataset expected={expectedSelection} />;
    const salesBrands = [...brandData].sort((a, b) => b.monthlySales - a.monthlySales);
    const revenueBrands = [...brandData].sort((a, b) => b.monthlyRevenue - a.monthlyRevenue);
    const brandScatterData: BrandScatterPoint[] = revenueBrands.map((item) => ({
      ...item,
      averagePriceCny: item.averagePrice * cnyRate(dataset),
      monthlyRevenueCny: item.monthlyRevenue * cnyRate(dataset),
    }));
    const topShare = (count: number) => totalSales ? salesBrands.slice(0, count).reduce((value, item) => value + item.monthlySales, 0) / totalSales : 0;
    const brandShare = salesBrands.length > 8
      ? [
          ...salesBrands.slice(0, 7).map((item) => ({ name: item.name, value: totalSales ? item.monthlySales / totalSales : 0 })),
          { name: "其他品牌", value: totalSales ? salesBrands.slice(7).reduce((value, item) => value + item.monthlySales, 0) / totalSales : 0 },
        ]
      : salesBrands.map((item) => ({ name: item.name, value: totalSales ? item.monthlySales / totalSales : 0 }));
    const filteredBrands = brandData
      .filter((item) => item.name.toLowerCase().includes(brandSearch.toLowerCase()))
      .sort((a, b) => {
        if (brandSort === "revenue") return b.monthlyRevenue - a.monthlyRevenue;
        if (brandSort === "price") return b.averagePrice - a.averagePrice;
        if (brandSort === "share") return (b.monthlySales / Math.max(totalSales, 1)) - (a.monthlySales / Math.max(totalSales, 1));
        return b.monthlySales - a.monthlySales;
      });
    const brandPriceHeatmapData = brandPriceHeatmap(baseProducts, dataset, effectiveCurrency, 5);
    const exportBrands = () => downloadCsv(
      `brands_${marketplace}_${category}_${date}.csv`,
      ["品牌", "商品数", "月销量", "月销售额", "销量加权均价", "月销量份额", "近一年销量", "近一年销售额"],
      filteredBrands.map((item) => [item.name, item.count, item.monthlySales, item.monthlyRevenue, item.averagePrice, totalSales ? item.monthlySales / totalSales : 0, "", ""]),
    );
    return <>
      <section className="kpi-grid five">
        <KpiCard icon={<Building2 />} tone="green" label="品牌数" value={brandData.length} note="全部清洗竞品的去重品牌" />
        <KpiCard icon={<Trophy />} tone="gold" label="第一品牌" value={salesBrands[0]?.name ?? "—"} note="按月销量" />
        <KpiCard icon={<Gauge />} tone="blue" label="第一品牌份额" value={percent(topShare(1))} note="月销量口径" />
        <KpiCard icon={<Layers3 />} tone="violet" label="Top3集中度" value={percent(topShare(3))} note="月销量口径" />
        <KpiCard icon={<Layers3 />} tone="coral" label="Top5集中度" value={percent(topShare(5))} note="月销量口径" />
      </section>
      <section className="analysis-grid two-column">
        <article className="chart-panel"><PanelTitle index="01" title="品牌月销量排名" note="按月销量排序" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={brandData.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 28 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={compact} /><YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 8 }} /><Tooltip formatter={(value) => whole(Number(value))} /><Bar dataKey="monthlySales" fill="#FF610A" /></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel"><PanelTitle index="02" title="品牌月销售额排名" note="按月销售额排序" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={revenueBrands.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 28 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={compact} /><YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 8 }} /><Tooltip formatter={(value) => displayMoney(Number(value), dataset, effectiveCurrency)} /><Bar dataKey="monthlyRevenue" fill="#c54808" /></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel"><PanelTitle index="03" title="品牌月销量份额" note="横向条形图 · 悬浮查看占比" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><BarChart data={brandShare} layout="vertical" margin={{ left: 8, right: 28 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tickFormatter={(value) => percent(Number(value), 0)} /><YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 8 }} /><Tooltip formatter={(value) => percent(Number(value))} /><Bar dataKey="value" name="月销量占比">{brandShare.map((item, index) => <Cell key={item.name} fill={item.name === "其他品牌" ? "#9aa7a1" : chartColors[index % chartColors.length]} />)}</Bar></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel"><PanelTitle index="04" title="品牌价格定位矩阵" note="横轴月销量 · 纵轴销量加权均价（人民币） · 气泡为月销售额（人民币）" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 12, right: 22, bottom: 8, left: 8 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="monthlySales" name="月销量" tickFormatter={compact} /><YAxis type="number" dataKey="averagePriceCny" name="销量加权均价" tickFormatter={(value) => currency(Number(value), "CNY")} width={72} /><ZAxis type="number" dataKey="monthlyRevenueCny" name="月销售额" range={[70, 700]} /><Tooltip content={<BrandScatterTooltip />} /><Scatter data={brandScatterData}>{brandScatterData.map((item, index) => <Cell key={item.name} fill={brandBubbleColor(index)} fillOpacity={0.84} stroke="rgba(255,255,255,.9)" strokeWidth={1} />)}</Scatter></ScatterChart></ResponsiveContainer></div><p className="chart-insight">用于识别高销量、高客单与高销售额的重点品牌；加权均价按月销售额 ÷ 月销量计算。</p></article>
      </section>
      <section className="chart-panel brand-price-heatmap-panel">
        <PanelTitle index="05" title="品牌 × 价格段热力图" note={`最多显示 Top5 品牌 · 单元格为榜单月销量占比 · ${effectiveCurrency === "CNY" ? "人民币" : dataset.currency.code}`} />
        <div className="brand-price-heatmap">
          {brandPriceHeatmapData.rows.length === 0 ? (
            <div className="brand-price-heatmap-empty">当前筛选下暂无可用于价格带分析的品牌数据</div>
          ) : (
            <>
              <div
                className="brand-price-heatmap-grid brand-price-heatmap-head"
                style={{ gridTemplateColumns: `minmax(140px, 1.25fr) repeat(${brandPriceHeatmapData.bands.length}, minmax(110px, 1fr))` }}
              >
                <span>品牌 / 价格带</span>
                {brandPriceHeatmapData.bands.map((band) => <strong key={band.label}>{band.label}</strong>)}
              </div>
              {brandPriceHeatmapData.rows.map((row) => (
                <div
                  className="brand-price-heatmap-grid brand-price-heatmap-row"
                  key={row.brand}
                  style={{ gridTemplateColumns: `minmax(140px, 1.25fr) repeat(${brandPriceHeatmapData.bands.length}, minmax(110px, 1fr))` }}
                >
                  <strong>{row.brand}</strong>
                  {row.cells.map((cell, index) => {
                    const band = brandPriceHeatmapData.bands[index];
                    return (
                      <span
                        key={band.label}
                        style={brandHeatCellStyle(cell.share, brandPriceHeatmapData.maxShare)}
                        title={`${row.brand} · ${band.label}：${percent(cell.share, 2)} · 月销量 ${whole(cell.sales)} · 商品数 ${cell.products}`}
                      >
                        {percent(cell.share, 2)}
                      </span>
                    );
                  })}
                </div>
              ))}
            </>
          )}
        </div>
        <p className="chart-insight">按完整清洗竞品池计算；热力图固定最多显示月销量最高的 5 个品牌，单元格为该品牌在价格带内的月销量占全榜单月销量比例。</p>
      </section>
      <section className="product-panel">
        <PanelTitle index="06" title="品牌明细" note={`${filteredBrands.length} 个品牌`} action={<Button size="sm" variant="outline" onClick={exportBrands}><Download />导出 CSV</Button>} />
        <div className="table-toolbar brand-tools"><label className="search-box"><Search /><input value={brandSearch} onChange={(event) => setBrandSearch(event.target.value)} placeholder="搜索品牌" /></label><span>近一年销量与销售额：源Excel未提供，显示为 —</span><Select value={brandSort} onValueChange={(value) => setBrandSort(value as typeof brandSort)}><SelectTrigger className="sort-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="sales">按月销量</SelectItem><SelectItem value="revenue">按月销售额</SelectItem><SelectItem value="price">按加权均价</SelectItem><SelectItem value="share">按市场份额</SelectItem></SelectContent></Select></div>
        <div className="product-table-wrap"><Table><TableHeader><TableRow><TableHead>品牌</TableHead><TableHead>商品数</TableHead><TableHead>月销量</TableHead><TableHead>月销售额</TableHead><TableHead>销量加权均价</TableHead><TableHead>市场份额</TableHead><TableHead>近一年销量</TableHead><TableHead>近一年销售额</TableHead><TableHead>查看</TableHead></TableRow></TableHeader><TableBody>{filteredBrands.map((item) => <TableRow key={item.name}><TableCell><strong>{item.name}</strong></TableCell><TableCell>{item.count}</TableCell><TableCell>{whole(item.monthlySales)}</TableCell><TableCell>{displayMoney(item.monthlyRevenue, dataset, effectiveCurrency)}</TableCell><TableCell>{displayMoney(item.averagePrice, dataset, effectiveCurrency)}</TableCell><TableCell>{percent(totalSales ? item.monthlySales / totalSales : 0)}</TableCell><TableCell>—</TableCell><TableCell>—</TableCell><TableCell><Button size="icon" variant="ghost" onClick={() => { setBrandFilter(item.name); activatePage("products"); }}><PackageSearch /></Button></TableCell></TableRow>)}</TableBody></Table></div>
      </section>
    </>;
  };

  const ProductTable = ({ products }: { products: Product[] }) => (
    <div className="product-table-wrap monitoring-table"><Table><TableHeader><TableRow><TableHead>榜单名次</TableHead><TableHead>商品</TableHead><TableHead>品牌</TableHead><TableHead>月销量 / 变化率</TableHead><TableHead>月销售额 / 变化率</TableHead><TableHead>价格 / 变化率</TableHead><TableHead>小类BSR（本周 / 上周）</TableHead><TableHead>排名变化</TableHead><TableHead>评分 / 评价数</TableHead><TableHead>月新增评价</TableHead><TableHead>上架时间 / 生命周期</TableHead><TableHead>当前榜单权益</TableHead><TableHead>权益变化</TableHead><TableHead>操作</TableHead></TableRow></TableHeader><TableBody>{products.map((product) => {
      const weekly = changes.find((item) => item.asin === product.asin);
      const rateClass = (value: number | null) => value == null || value === 0 ? "rank-flat" : value > 0 ? "rank-up" : "rank-down";
      const rateValue = (value: number | null) => value == null ? "暂无上期" : value === 0 ? "—" : `${value > 0 ? "+" : ""}${percent(value)}`;
      const rankTrend = !weekly ? <span className="rank-flat">—</span> : !weekly.previous ? <span className="rank-new">NEW</span> : weekly.rankChange == null || weekly.rankChange === 0 ? <span className="rank-flat">—</span> : weekly.rankChange > 0 ? <span className="rank-up">↑ {weekly.rankChange}</span> : <span className="rank-down">↓ {Math.abs(weekly.rankChange)}</span>;
      return <TableRow key={product.asin} className="clickable-row"><TableCell><div className="rank-cell"><strong>{product.rank ?? productRank(product) ?? "—"}</strong></div></TableCell><TableCell><button className="product-identity" onClick={() => setSelectedProduct(product)}>{product.imageUrl ? <img src={product.imageUrl} alt="" /> : <span className="image-placeholder"><PackageSearch /></span>}<span><strong>{product.shortTitle || product.title}</strong><small>{product.asin}</small></span></button></TableCell><TableCell>{product.brand || "Unknown"}</TableCell><TableCell className="numeric"><strong>{whole(product.monthlySales)}</strong><small className={rateClass(weekly?.salesRate ?? null)}>{rateValue(weekly?.salesRate ?? null)}</small></TableCell><TableCell className="numeric"><strong>{dataset ? displayMoney(product.monthlyRevenue, dataset, effectiveCurrency) : "—"}</strong><small className={rateClass(weekly?.revenueRate ?? null)}>{rateValue(weekly?.revenueRate ?? null)}</small></TableCell><TableCell className="numeric"><strong>{dataset ? displayMoney(product.price, dataset, effectiveCurrency) : "—"}</strong><small className={rateClass(weekly?.priceRate ?? null)}>{rateValue(weekly?.priceRate ?? null)}</small></TableCell><TableCell className="numeric"><div className="bsr-rank-value"><strong>{productRank(product) ?? "—"}</strong>{weekly?.previousRank == null && <span>无上周数据</span>}</div>{weekly?.previousRank != null && <small>上周 {weekly.previousRank}</small>}</TableCell><TableCell>{rankTrend}</TableCell><TableCell><div className="rating-cell"><Star />{product.rating ?? "—"}<span>{whole(product.reviewCount)}</span></div></TableCell><TableCell className="numeric">{whole(product.newReviewCount)}</TableCell><TableCell className="lifecycle-cell"><strong>{product.listedDate || "—"}</strong>{(product.listingDays ?? 999999) <= 365 && <small className="product-new">一年内新品</small>}</TableCell><TableCell className="rights-text">{rightsLabel(product)}</TableCell><TableCell className="rights-change">{weekly?.rightsChanged ? rightsDelta(product, weekly.previous) : "—"}</TableCell><TableCell><div className="row-actions"><Button size="icon" variant="ghost" onClick={() => setSelectedProduct(product)} title="打开商品详情"><PackageSearch /></Button><Button size="icon" variant="ghost" onClick={() => hideProduct(product.asin)} title="本次查看中隐藏"><EyeOff /></Button>{product.productUrl && <Button size="icon" variant="ghost" asChild><a href={product.productUrl} target="_blank" rel="noreferrer" title="打开Amazon商品页"><ExternalLink /></a></Button>}</div></TableCell></TableRow>;
    })}</TableBody></Table></div>
  );

  const ProductsPage = () => {
    if (!dataset) return <EmptyDataset expected={expectedSelection} />;
    const badgeMetrics = ([
      { key: "bestSeller", label: "Best Seller", value: baseProducts.filter((item) => item.badges.bestSeller).length },
      { key: "amazonChoice", label: "Amazon's Choice", value: baseProducts.filter((item) => item.badges.amazonChoice).length },
      { key: "newRelease", label: "New Release", value: baseProducts.filter((item) => item.badges.newRelease).length },
      { key: "coupon", label: "Coupon", value: baseProducts.filter((item) => item.badges.cpf).length },
    ] satisfies Array<{ key: ProductMetricFilter; label: string; value: number }>);
    const contentMetrics = ([
      { key: "aPlus", label: "A+ 页面", value: baseProducts.filter((item) => item.content.aPlus).length },
      { key: "video", label: "视频", value: baseProducts.filter((item) => item.content.video).length },
      { key: "brandStory", label: "品牌故事", value: baseProducts.filter((item) => item.content.brandStory).length },
      { key: "spAds", label: "SP广告", value: baseProducts.filter((item) => item.content.spAds).length },
      { key: "brandAds", label: "品牌广告", value: baseProducts.filter((item) => item.content.brandAds).length },
    ] satisfies Array<{ key: ProductMetricFilter; label: string; value: number }>);
    const allMetrics = [...badgeMetrics, ...contentMetrics];
    const zeroMetrics = allMetrics.filter((item) => item.value === 0);
    const visibleMetrics = (items: typeof allMetrics) => items.filter((item) => item.value > 0 || showZeroMetrics);
    const matchesMetric = (product: Product) => {
      if (productMetricFilter === "all") return true;
      if (productMetricFilter === "bestSeller") return product.badges.bestSeller;
      if (productMetricFilter === "amazonChoice") return product.badges.amazonChoice;
      if (productMetricFilter === "newRelease") return product.badges.newRelease;
      if (productMetricFilter === "coupon") return product.badges.cpf;
      return Boolean(product.content[productMetricFilter as keyof Product["content"]]);
    };
    const search = productSearch.trim().toLowerCase();
    const tableProducts = baseProducts
      .filter((product) => !brandFilter || product.brand === brandFilter)
      .filter(matchesMetric)
      .filter((product) => !search || [product.asin, product.brand, product.shortTitle, product.title].some((value) => value?.toLowerCase().includes(search)))
      .sort((a, b) => {
        if (productSort === "sales") return (b.monthlySales ?? 0) - (a.monthlySales ?? 0);
        if (productSort === "revenue") return (b.monthlyRevenue ?? 0) - (a.monthlyRevenue ?? 0);
        if (productSort === "price") return (b.price ?? 0) - (a.price ?? 0);
        if (productSort === "rating") return (b.rating ?? 0) - (a.rating ?? 0);
        return (productRank(a) ?? 9999) - (productRank(b) ?? 9999);
      }).slice(0, topN);
    const bandData = priceBands(baseProducts, dataset, effectiveCurrency);
    const scatterData: ProductScatterPoint[] = baseProducts.filter((item) => item.price != null && item.monthlySales != null).map((item) => ({ ...item, x: converted(item.price, dataset, effectiveCurrency) ?? 0, y: item.monthlySales ?? 0, z: converted(item.monthlyRevenue, dataset, effectiveCurrency) ?? 0, name: item.shortTitle, model: productModel(item) }));
    const newProducts = baseProducts.filter((item) => (item.listingDays ?? 999999) <= 365).length;
    const priceMetricLabels: Record<PriceMetric, string> = { products: "商品数", monthlySales: "月销量", monthlyRevenue: "月销售额" };
    const MetricCard = ({ item }: { item: (typeof allMetrics)[number] }) => <button key={item.key} className={productMetricFilter === item.key ? "active" : ""} onClick={() => setProductMetricFilter(item.key)}><span>{item.label}</span><strong>{item.value}</strong><small>覆盖率 {percent(baseProducts.length ? item.value / baseProducts.length : 0)}</small></button>;
    const exportProducts = () => downloadCsv(
      `products_${marketplace}_${category}_${date}_Top${topN}.csv`,
      ["榜单名次", "商品名称", "品牌", "ASIN", "商品链接", "价格", "月销量", "月销售额", "月销量变化率", "月销售额变化率", "价格变化率", "当前小类BSR", "上周BSR", "BSR排名变化", "评分", "评价数", "月新增评价数", "上架时间", "一年内新品", "当前榜单权益", "权益变化"],
      tableProducts.map((item) => { const weekly = changes.find((row) => row.asin === item.asin); return [item.rank ?? productRank(item), item.shortTitle || item.title, item.brand, item.asin, item.productUrl, item.price, item.monthlySales, item.monthlyRevenue, weekly?.salesRate, weekly?.revenueRate, weekly?.priceRate, productRank(item), weekly?.previousRank, weekly?.rankChange, item.rating, item.reviewCount, item.newReviewCount, item.listedDate, (item.listingDays ?? 999999) <= 365 ? "是" : "否", rightsLabel(item), weekly?.rightsChanged ? rightsDelta(item, weekly.previous) : ""]; }),
    );
    return <>
      <section className="kpi-grid">
        <KpiCard icon={<PackageSearch />} tone="green" label="有效商品" value={baseProducts.length} note="全部清洗竞品" />
        <KpiCard icon={<Tags />} tone="gold" label="销量加权均价" value={displayMoney(weightedAveragePrice(baseProducts), dataset, effectiveCurrency)} note="月销售额 ÷ 月销量" />
        <KpiCard icon={<Star />} tone="blue" label="平均评分" value={average(baseProducts, "rating").toFixed(1)} note="有效评分简单平均" />
        <KpiCard icon={<Sparkles />} tone="violet" label="一年内新品" value={newProducts} note="上架不超过365天" />
        <KpiCard icon={<BadgeCheck />} tone="coral" label="Best Seller" value={baseProducts.filter((item) => item.badges.bestSeller).length} note="徽章覆盖商品" />
        <KpiCard icon={<Trophy />} tone="slate" label="Amazon's Choice" value={baseProducts.filter((item) => item.badges.amazonChoice).length} note="徽章覆盖商品" />
      </section>
      <section className="analysis-grid two-column">
        <article className="chart-panel"><PanelTitle index="01" title={`各价格带${priceMetricLabels[priceMetric]}贡献`} note="使用统一细分价格段 · 可切换商品数 / 月销量 / 月销售额" action={<Select value={priceMetric} onValueChange={(value) => setPriceMetric(value as PriceMetric)}><SelectTrigger className="metric-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="products">商品数</SelectItem><SelectItem value="monthlySales">月销量</SelectItem><SelectItem value="monthlyRevenue">月销售额</SelectItem></SelectContent></Select>} /><div className="chart-box price-band-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={bandData} margin={{ bottom: 30 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" interval={0} angle={-35} textAnchor="end" height={58} tick={{ fontSize: 8 }} /><YAxis tickFormatter={compact} /><Tooltip formatter={(value) => priceMetric === "monthlyRevenue" ? currency(Number(value), effectiveCurrency === "CNY" ? "CNY" : dataset.currency.code) : whole(Number(value))} /><Bar dataKey={priceMetric} fill="#f7b32b" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div></article>
        <article className="chart-panel"><PanelTitle index="02" title="价格 × 月销量产品分布" note="气泡大小代表月销售额，颜色区分品牌；悬浮查看品牌与型号" /><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="x" name="价格" tickFormatter={compact} /><YAxis type="number" dataKey="y" name="月销量" tickFormatter={compact} /><ZAxis type="number" dataKey="z" range={[45, 500]} /><Tooltip content={<ProductScatterTooltip currencyCode={effectiveCurrency === "CNY" ? "CNY" : dataset.currency.code} />} /><Scatter data={scatterData}>{scatterData.map((item, index) => <Cell key={item.asin} fill={chartColors[(brandData.findIndex((brand) => brand.name === item.brand) + chartColors.length) % chartColors.length] ?? chartColors[index % chartColors.length]} />)}</Scatter></ScatterChart></ResponsiveContainer></div></article>
      </section>
      <section className="chart-panel metrics-panel"><PanelTitle index="03" title="榜单权益与内容配置" note="每项显示覆盖商品数与覆盖率；点击卡片筛选商品" /><div className="metric-cards"><button className={productMetricFilter === "all" ? "active" : ""} onClick={() => setProductMetricFilter("all")}><span>全部商品</span><strong>{baseProducts.length}</strong><small>覆盖率 100%</small></button><div className="metric-group"><div className="metric-group-title"><BadgeCheck /><span>榜单权益</span></div><div className="metric-group-cards">{visibleMetrics(badgeMetrics).map((item) => <MetricCard key={item.key} item={item} />)}</div></div><div className="metric-group"><div className="metric-group-title"><Layers3 /><span>内容配置</span></div><div className="metric-group-cards">{visibleMetrics(contentMetrics).map((item) => <MetricCard key={item.key} item={item} />)}</div></div>{zeroMetrics.length > 0 && <button className="metric-more-button" onClick={() => { if (showZeroMetrics && zeroMetrics.some((item) => item.key === productMetricFilter)) setProductMetricFilter("all"); setShowZeroMetrics((current) => !current); }}>{showZeroMetrics ? "收起零覆盖指标" : `更多指标（${zeroMetrics.length}）`}</button>}</div></section>
      <section className="product-panel"><PanelTitle index="04" title={`Top ${topN} 商品综合监控`} note={`${tableProducts.length} 条筛选结果`} action={<Button size="sm" variant="outline" onClick={exportProducts}><Download />导出 CSV</Button>} /><div className="table-toolbar product-tools"><label className="search-box"><Search /><input value={productSearch} onChange={(event) => setProductSearch(event.target.value)} placeholder="搜索 ASIN / 品牌 / 商品" /></label><Select value={brandFilter || "__all"} onValueChange={(value) => setBrandFilter(value === "__all" ? "" : value)}><SelectTrigger className="brand-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="__all">全部品牌</SelectItem>{brandData.map((item) => <SelectItem key={item.name} value={item.name}>{item.name}</SelectItem>)}</SelectContent></Select><Select value={productSort} onValueChange={(value) => setProductSort(value as typeof productSort)}><SelectTrigger className="sort-select"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="rank">按BSR</SelectItem><SelectItem value="sales">按月销量</SelectItem><SelectItem value="revenue">按月销售额</SelectItem><SelectItem value="price">按价格</SelectItem><SelectItem value="rating">按评分</SelectItem></SelectContent></Select>{hiddenAsins.size > 0 && <button className="link-button" onClick={() => setHiddenAsins(new Set())}>恢复 {hiddenAsins.size} 个隐藏商品</button>}</div><div className="bsr-definition"><Info /><span><strong>BSR 官方口径：</strong>商品在同一亚马逊类目中的销售排名。亚马逊根据销量数据计算，并同时参考近期及历史销量，其中近期销量权重更高；数值越小，代表销售排名越靠前。</span><a href="https://sell.amazon.com/blog/amazon-best-sellers-rank" target="_blank" rel="noreferrer">查看官方说明<ExternalLink /></a></div><ProductTable products={tableProducts} /></section>
    </>;
  };

  const WeeklyPage = () => {
    if (!dataset) return <EmptyDataset expected={expectedSelection} />;
    if (previousDataset && !sameCoverage(dataset, previousDataset)) return <section className="weekly-empty"><h2>来源榜单范围已变化</h2><p>本期补入了其他榜单的竞品，不能把新增覆盖当作销量增长。下一期按相同来源采集后恢复比较。</p></section>;
    if (!previousDataset) return <section className="weekly-empty"><div className="empty-icon"><History /></div><p>周度异动</p><h2>暂无可对比的上一期数据</h2><span>当前只有 {date} 的同站点同品类数据。下周上传新Excel并重新构建后，本页会自动比较最近两期，不需要另外整理周报。</span><div className="weekly-empty-rules"><strong>第二期数据接入后自动生成</strong><span>排名上升、下降与不变商品数</span><span>排名升降幅度Top20</span><span>月销售额增长与下降Top20</span><span>月销量增长与价格变化Top20</span><span>Top20新进榜与跌出榜商品</span><span>榜单权益新增与失去</span></div></section>;
    const weeklyTier = Math.min(topN, 20);
    const currentTop20 = new Set(baseProducts.slice(0, weeklyTier).map((item) => item.asin));
    const previousTop20 = new Set(previousBaseProducts.slice(0, weeklyTier).map((item) => item.asin));
    const entered = changes.filter((item) => currentTop20.has(item.asin) && !previousTop20.has(item.asin));
    const exited = changes.filter((item) => !currentTop20.has(item.asin) && previousTop20.has(item.asin));
    const rises = changes.filter((item) => (item.rankChange ?? 0) > 0).sort((a, b) => (b.rankChange ?? 0) - (a.rankChange ?? 0));
    const falls = changes.filter((item) => (item.rankChange ?? 0) < 0).sort((a, b) => (a.rankChange ?? 0) - (b.rankChange ?? 0));
    const unchanged = changes.filter((item) => item.rankChange === 0);
    const revenueGrowth = changes.filter((item) => (item.revenueRate ?? 0) > 0).sort((a, b) => (b.revenueRate ?? 0) - (a.revenueRate ?? 0));
    const revenueDecline = changes.filter((item) => (item.revenueRate ?? 0) < 0).sort((a, b) => (a.revenueRate ?? 0) - (b.revenueRate ?? 0));
    const salesGrowth = changes.filter((item) => (item.salesRate ?? 0) > 0).sort((a, b) => (b.salesRate ?? 0) - (a.salesRate ?? 0));
    const priceMoves = changes.filter((item) => item.priceRate != null && item.priceRate !== 0).sort((a, b) => Math.abs(b.priceRate ?? 0) - Math.abs(a.priceRate ?? 0));
    const rightsMoves = changes.filter((item) => item.rightsChanged);

    const RankChangePanel = ({ index, title, rows, direction }: { index: string; title: string; rows: WeeklyRow[]; direction: "up" | "down" }) => {
      const shown = rows.slice(0, weeklyTier); const maxChange = Math.max(...shown.map((item) => Math.abs(item.rankChange ?? 0)), 1);
      return <article className="chart-panel weekly-rank-panel"><PanelTitle index={index} title={title} note="变化名次 = 上周排名 − 本周排名" /><div className="weekly-rank-list">{shown.map((item) => <button key={item.asin} onClick={() => setSelectedProduct(item.product)}><span className="weekly-rank-name"><strong>{item.product.shortTitle || item.product.title}</strong><small>上周 {item.previousRank ?? "—"} → 本周 {item.currentRank ?? "—"}</small></span><span className="weekly-rank-bar"><i className={direction} style={{ width: `${Math.max(Math.abs(item.rankChange ?? 0) / maxChange * 100, 4)}%` }} /></span><em className={direction === "up" ? "rank-up" : "rank-down"}>{direction === "up" ? `↑ ${item.rankChange}` : `↓ ${Math.abs(item.rankChange ?? 0)}`}</em></button>)}{shown.length === 0 && <p>本期没有符合条件的商品</p>}</div></article>;
    };

    const PerformanceList = ({ index, title, rows, metric }: { index: string; title: string; rows: WeeklyRow[]; metric: "revenue" | "sales" | "price" }) => {
      const shown = rows.slice(0, weeklyTier);
      const values = (item: WeeklyRow) => {
        if (metric === "sales") return { now: whole(item.product.monthlySales), before: whole(item.previous?.monthlySales), rate: item.salesRate };
        if (metric === "price") return { now: displayMoney(item.product.price, dataset, effectiveCurrency), before: displayMoney(item.previous?.price, previousDataset, effectiveCurrency), rate: item.priceRate };
        return { now: displayMoney(item.product.monthlyRevenue, dataset, effectiveCurrency), before: displayMoney(item.previous?.monthlyRevenue, previousDataset, effectiveCurrency), rate: item.revenueRate };
      };
      return <article className="chart-panel"><PanelTitle index={index} title={title} note={`显示 Top ${Math.min(shown.length, weeklyTier)}`} /><div className="weekly-performance-list">{shown.map((item) => { const value = values(item); return <button key={item.asin} onClick={() => setSelectedProduct(item.product)}><span className="weekly-performance-name"><strong>{item.product.shortTitle || item.product.title}</strong><small>{item.product.brand || "Unknown"} · {item.asin}</small></span><span><small>本周</small><strong>{value.now}</strong></span><span><small>上周</small><strong>{value.before}</strong></span><em className={(value.rate ?? 0) > 0 ? "rank-up" : (value.rate ?? 0) < 0 ? "rank-down" : "rank-flat"}>{value.rate == null ? "—" : `${(value.rate ?? 0) > 0 ? "+" : ""}${percent(value.rate)}`}</em></button>; })}{shown.length === 0 && <p>本期没有符合条件的商品</p>}</div></article>;
    };

    const TransitionTable = ({ index, title, rows, mode }: { index: string; title: string; rows: WeeklyRow[]; mode: "entered" | "exited" }) => <section className="product-panel weekly-transition-panel"><PanelTitle index={index} title={title} note={`${rows.length} 个商品`} /><div className="product-table-wrap weekly-table"><Table><TableHeader><TableRow><TableHead>商品</TableHead><TableHead>品牌</TableHead><TableHead>{mode === "entered" ? "本周排名" : "上周排名"}</TableHead><TableHead>月销量</TableHead><TableHead>月销售额</TableHead><TableHead>榜单权益</TableHead></TableRow></TableHeader><TableBody>{rows.map((item) => { const product = mode === "entered" ? item.product : item.previous ?? item.product; return <TableRow key={item.asin} className="clickable-row" onClick={() => setSelectedProduct(product)}><TableCell><strong>{product.shortTitle || product.title}</strong><small>{item.asin}</small></TableCell><TableCell>{product.brand || "Unknown"}</TableCell><TableCell>{mode === "entered" ? item.currentRank ?? "—" : item.previousRank ?? "—"}</TableCell><TableCell>{whole(product.monthlySales)}</TableCell><TableCell>{displayMoney(product.monthlyRevenue, mode === "entered" ? dataset : previousDataset, effectiveCurrency)}</TableCell><TableCell className="rights-text">{rightsLabel(product)}</TableCell></TableRow>; })}{rows.length === 0 && <TableRow><TableCell colSpan={6} className="weekly-table-empty">本期没有符合条件的商品</TableCell></TableRow>}</TableBody></Table></div></section>;

    return <>
      <section className="kpi-grid">
        <KpiCard icon={<ArrowUp />} tone="green" label="排名上升商品数" value={rises.length} note={`对比 ${previousDataset.date}`} />
        <KpiCard icon={<ArrowDown />} tone="coral" label="排名下降商品数" value={falls.length} note={`对比 ${previousDataset.date}`} />
        <KpiCard icon={<ArrowRightLeft />} tone="blue" label="排名不变商品数" value={unchanged.length} note="两期均在榜且名次相同" />
        <KpiCard icon={<Sparkles />} tone="gold" label={`新进Top${weeklyTier}商品数`} value={entered.length} note={`本周进入竞品Top${weeklyTier}`} />
        <KpiCard icon={<TrendingDown />} tone="violet" label={`跌出Top${weeklyTier}商品数`} value={exited.length} note="上周在榜、本周跌出" />
        <KpiCard icon={<BadgeCheck />} tone="slate" label="榜单权益变化商品数" value={rightsMoves.length} note="徽章新增或失去" />
      </section>
      <section className="analysis-grid two-column"><RankChangePanel index="01" title={`排名上升幅度 Top${weeklyTier}`} rows={rises} direction="up" /><RankChangePanel index="02" title={`排名下降幅度 Top${weeklyTier}`} rows={falls} direction="down" /></section>
      <section className="analysis-grid two-column"><PerformanceList index="03" title={`月销售额增长 Top${weeklyTier}`} rows={revenueGrowth} metric="revenue" /><PerformanceList index="04" title={`月销售额下降 Top${weeklyTier}`} rows={revenueDecline} metric="revenue" /><PerformanceList index="05" title={`月销量增长 Top${weeklyTier}`} rows={salesGrowth} metric="sales" /><PerformanceList index="06" title={`价格变化 Top${weeklyTier}`} rows={priceMoves} metric="price" /></section>
      <section className="analysis-grid two-column weekly-transition-grid"><TransitionTable index="07" title={`Top${weeklyTier}新进榜商品`} rows={entered} mode="entered" /><TransitionTable index="08" title={`Top${weeklyTier}跌出榜商品`} rows={exited} mode="exited" /></section>
      <section className="product-panel weekly-rights-panel"><PanelTitle index="09" title="榜单权益变化" note="Best Seller / Amazon's Choice / New Release / Coupon" /><div className="product-table-wrap weekly-table"><Table><TableHeader><TableRow><TableHead>商品</TableHead><TableHead>品牌</TableHead><TableHead>上周权益</TableHead><TableHead>本周权益</TableHead><TableHead>变化</TableHead></TableRow></TableHeader><TableBody>{rightsMoves.map((item) => <TableRow key={item.asin} className="clickable-row" onClick={() => setSelectedProduct(item.product)}><TableCell><strong>{item.product.shortTitle || item.product.title}</strong><small>{item.asin}</small></TableCell><TableCell>{item.product.brand || "Unknown"}</TableCell><TableCell className="rights-text">{item.previousRights}</TableCell><TableCell className="rights-text">{item.currentRights}</TableCell><TableCell className="rights-change">{rightsDelta(item.product, item.previous)}</TableCell></TableRow>)}{rightsMoves.length === 0 && <TableRow><TableCell colSpan={5} className="weekly-table-empty">本期没有榜单权益变化</TableCell></TableRow>}</TableBody></Table></div></section>
    </>;
  };

  const GuidePage = () => {
    const pageGuide = [
      { index: "01", title: "总览", purpose: "先快速看懂这个市场", focus: "市场大不大、平均价格多少、有哪些主要品牌、哪些商品卖得好", use: "第一次打开看板时，建议先看这里" },
      { index: "00", title: "榜单追踪", purpose: "按Amazon榜单顺序看具体商品", focus: "商品排第几、价格多少、评价怎么样、排名有没有上升或下降", use: "想找某个竞品，或者想打开Amazon商品页时" },
      { index: "02", title: "机会对比", purpose: "把不同国家放在一起比较", focus: "哪个国家销量更高、销售额更大、价格更高、综合机会更好", use: "想决定先关注哪个国家市场时" },
      { index: "03", title: "品牌", purpose: "看各个品牌在市场里的表现", focus: "谁卖得最多、谁销售额最高、各品牌主要卖什么价格", use: "想研究Tineco、Bissell、Shark等品牌时" },
      { index: "04", title: "产品", purpose: "看每一个商品的详细表现", focus: "价格、销量、销售额、评分、评价数、上架时间和页面内容", use: "想做具体竞品分析或选品时" },
      { index: "05", title: "周度异动", purpose: "看这次数据和上次相比发生了什么", focus: "哪些商品排名上升、哪些下降、哪些新进榜、哪些跌出榜", use: "做每周市场复盘时" },
      { index: "07", title: "数据覆盖", purpose: "看哪些站点和品类已经有数据", focus: "哪些格子已经接入，哪些还没有上传", use: "更新数据后检查是否成功时" },
    ];
    const glossary = [
      ["Top10 / Top20 / Top30 / Top50", "决定商品列表显示前多少名。市场规模、品牌份额和其他市场统计始终按完整清洗竞品池计算。"],
      ["BSR", "Amazon的商品排名。数字越小，排名越靠前；第1名最好。"],
      ["ASIN", "Amazon给每个商品的编号，可以把它理解成商品的身份证。"],
      ["月销量", "工具估算这个商品一个月大约卖了多少件。"],
      ["月销售额", "工具估算这个商品一个月大约卖了多少钱。"],
      ["销量加权均价", "用月销售额除以月销量，代表这些商品更接近实际销售情况的平均价格。"],
      ["市场份额", "一个品牌或商品在当前榜单中占了多大比例。"],
      ["榜单权益", "商品是否有Best Seller、Amazon's Choice、New Release或Coupon等标识。"],
      ["一年内新品", "上架时间不超过一年的商品。"],
      ["— / Unknown", "“—”表示没有这项数据；Unknown表示暂时没有识别出品牌。"],
    ];
    return <div className="guide-page">
      <section className="guide-hero">
        <div className="guide-hero-copy"><span>第一次使用看这里</span><h2>这个看板，是用来快速看市场和竞品的</h2><p>你可以用它查看不同国家、不同清洁家电品类的Amazon榜单，了解哪些品牌和商品卖得好、价格是多少，以及最近的排名变化。不需要先懂数据分析，先选好国家和品类，再从“总览”开始看就可以。</p><nav className="guide-jump" aria-label="数据指南目录"><a href="#guide-start">第一次怎么用</a><a href="#guide-filters">顶部筛选</a><a href="#guide-pages">各个模块</a><a href="#guide-charts">图表怎么看</a><a href="#guide-words">常见名词</a><a href="#guide-questions">我该去哪里看</a></nav></div>
        <div className="guide-grain-card"><BookOpen /><small>最简单的使用方法</small><strong>选国家 → 选品类 → 选Top范围 → 看总览</strong><div><span>选站点</span><i>→</i><span>选品类</span><i>→</i><span>选Top N</span><i>→</i><span>看结果</span></div><p>不知道点哪里时，按照这个顺序操作即可。</p></div>
      </section>

      <section className="guide-panel" id="guide-start"><PanelTitle index="01" title="第一次打开，按这四步操作" note="不需要设置其他内容" /><div className="guide-levels beginner-steps">
        <article><b>01</b><span>选择国家</span><strong>先选Amazon站点</strong><p>例如美国站、英国站、德国站或日本站。你想研究哪个国家，就选哪个。</p></article>
        <article><b>02</b><span>选择产品</span><strong>再选清洁家电品类</strong><p>可以选择除螨仪、布艺清洗机、洗地机、扫地机器人或吸尘器。</p></article>
        <article><b>03</b><span>选择范围</span><strong>决定看前多少名</strong><p>第一次建议选择Top50，信息最完整；只想快速看头部商品时可以选Top10。</p></article>
        <article><b>04</b><span>开始浏览</span><strong>先进入“总览”</strong><p>先看市场整体情况，再根据你的问题进入品牌、产品或周度异动页面。</p></article>
      </div></section>

      <section className="guide-panel" id="guide-filters"><PanelTitle index="02" title="顶部这些按钮是什么意思" note="这些选择会同时影响各个业务页面" /><div className="guide-filter-grid">
        <article><span>站点</span><strong>选择国家</strong><p>决定你现在看美国、英国、德国、法国、意大利、西班牙还是日本的Amazon数据。</p></article>
        <article><span>品类</span><strong>选择产品类型</strong><p>决定你现在看除螨仪、布艺清洗机、洗地机、扫地机器人还是吸尘器。</p></article>
        <article><span>数据日期</span><strong>选择哪一次更新的数据</strong><p>一般直接选择最新日期；想查看以前的情况时，再切换到旧日期。</p></article>
        <article><span>金额单位</span><strong>选择显示什么货币</strong><p>看单个国家时可以用当地货币；比较多个国家时可以统一看人民币。</p></article>
        <article><span>Top10 / 20 / 30 / 50</span><strong>选择商品列表展示范围</strong><p>数字越大，列表显示的商品越多。品牌份额和市场规模始终基于完整清洗后的竞品池。</p></article>
        <article><span>重置</span><strong>恢复最初状态</strong><p>如果你改了很多选择，不知道怎么恢复，点击“重置”即可。</p></article>
      </div></section>

      <section className="guide-panel" id="guide-pages"><PanelTitle index="03" title="左侧每个模块是干什么的" note="按照你想解决的问题选择页面" /><div className="guide-page-grid">{pageGuide.map((item) => <article key={item.title}><header><span>{item.index}</span><strong>{item.title}</strong></header><h3>{item.purpose}</h3><dl><div><dt>里面有</dt><dd>{item.focus}</dd></div><div><dt>什么时候看</dt><dd>{item.use}</dd></div></dl></article>)}</div></section>

      <section className="guide-panel" id="guide-charts"><PanelTitle index="04" title="常见图表怎么看" note="记住下面几句话就够了" /><div className="guide-chart-grid">
        <article><BarChart3 /><strong>条形图</strong><p>条越长，代表这个品牌、商品或国家对应的数字越大。直接比较条的长短即可。</p></article>
        <article><CircleDollarSign /><strong>价格带图</strong><p>把商品按照价格分组，帮助你看哪个价位的商品卖得更多或销售额更高。</p></article>
        <article><Layers3 /><strong>热力图</strong><p>颜色越深，代表这个位置的数据越高。适合看品牌主要集中在哪些价格段。</p></article>
        <article><Activity /><strong>气泡图</strong><p>每个圆点代表一个品牌或商品。圆点越大，通常代表销售额越高；把鼠标放上去可以看详情。</p></article>
        <article><History /><strong>上升和下降</strong><p>绿色或向上的箭头表示表现变好；红色或向下的箭头表示表现下降。</p></article>
        <article><EyeOff /><strong>暂时不看某个商品</strong><p>点击小眼睛可以临时隐藏不相关商品，下面的商品会自动补上；刷新网页后会恢复。</p></article>
      </div></section>

      <section className="guide-panel" id="guide-words"><PanelTitle index="05" title="页面里常见的词是什么意思" note="用最简单的话解释" /><div className="guide-table-wrap"><table className="guide-table beginner-table"><thead><tr><th>页面上的词</th><th>简单理解</th></tr></thead><tbody>{glossary.map((row) => <tr key={row[0]}><th>{row[0]}</th><td>{row[1]}</td></tr>)}</tbody></table></div></section>

      <section className="guide-panel" id="guide-questions"><PanelTitle index="06" title="我想知道这些问题，应该去哪里看" note="直接找到对应模块" /><div className="guide-question-grid">
        <article><span>我想快速知道这个市场怎么样</span><strong>去“总览”</strong></article>
        <article><span>我想看Amazon榜单第1到第50名</span><strong>去“榜单追踪”</strong></article>
        <article><span>我想比较美国、英国、德国哪个机会更好</span><strong>去“机会对比”</strong></article>
        <article><span>我想知道哪个品牌卖得最好</span><strong>去“品牌”</strong></article>
        <article><span>我想查看某个商品的价格、销量和链接</span><strong>去“产品”或“榜单追踪”</strong></article>
        <article><span>我想知道本周哪些商品排名变化最大</span><strong>去“周度异动”</strong></article>
        <article><span>我刚上传了数据，想确认网站有没有读取</span><strong>去“数据覆盖”</strong></article>
      </div></section>

      <section className="guide-workflow"><BookOpen /><div><span>第一次使用推荐顺序</span><strong>选择站点和品类 → 打开总览 → 看品牌 → 看具体产品 → 下次更新数据后看周度异动</strong></div></section>
    </div>;
  };

  const CoveragePage = () => {
    const coveredForDate = dashboardData.datasets.filter((item) => item.date === date).length;
    return <>
      <section className="coverage-summary"><div><Database /><span><strong>{coveredForDate} / {dashboardData.expectedDatasetCount}</strong><small>{date} 已接入榜单</small></span></div><div><Gauge /><span><strong>{Math.round(coveredForDate / Math.max(dashboardData.expectedDatasetCount, 1) * 100)}%</strong><small>当前日期覆盖率</small></span></div><p>本页检查站点、品类和来源榜单是否完整。点击已接入单元格可切换到对应总览。</p></section>
      <section className="coverage-panel"><PanelTitle index="01" title="站点 × 品类数据覆盖矩阵" note={`数据日期 ${date}`} /><div className="coverage-grid">{marketplaces.map((market) => <div className="coverage-row" key={market}><strong>{marketplaceNames[market] ?? market}<small>{market}</small></strong>{categoryOptions.map((cat) => { const covered = dashboardData.datasets.find((item) => item.marketplace === market && item.category === cat.value && item.date === date); const available = Boolean(covered); return <button key={cat.value} className={available ? "available" : "pending"} onClick={() => { if (available) { setMarketplace(market); setCategory(cat.value); setDisplayCurrency("NATIVE"); clearTemporaryFilters(); activatePage("overview"); } }}><span>{cat.label}</span><small>{covered?.sourceCoverageComplete === false ? `缺少 ${covered.missingSourceNodes?.length ?? 0} 个来源` : available ? "已接入 · 查看总览" : "待导入"}</small></button>; })}</div>)}</div></section>
    </>;
  };

  const renderPage = () => {
    if (activePage === "tracker") return <TrackerPage />;
    if (activePage === "overview") return <OverviewPage />;
    if (activePage === "opportunity") return <OpportunityPage />;
    if (activePage === "brands") return <BrandsPage />;
    if (activePage === "products") return <ProductsPage />;
    if (activePage === "weekly") return <WeeklyPage />;
    if (activePage === "guide") return <GuidePage />;
    return <CoveragePage />;
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><span>MR</span><strong>市场雷达</strong></div>
        <nav>
          {navigationOrder.map((key) => { const item = pageMeta[key]; const Icon = item.icon; return <button key={key} className={activePage === key ? "active" : ""} onClick={() => activatePage(key)}><Icon /><span>{item.label}</span><small>{item.index}</small></button>; })}
        </nav>
        <button className="sidebar-coverage" onClick={() => activatePage("coverage")}><Database /><span>数据覆盖</span><strong>{dashboardData.loadedDatasetCount}<small>/{dashboardData.expectedDatasetCount}</small></strong></button>
        <div className="sidebar-note"><Activity /><span>数据状态随筛选实时同步</span></div>
      </aside>
      <main className="workspace">
        <header className="workspace-header"><div><div className="eyebrow">AMAZON MULTI-SITE MARKET RADAR</div><h1>清洁家电市场数据看板</h1><p>SellerSprite榜单数据 · 多站点市场洞察与Top N商品监控</p></div><div className="header-meta"><Badge variant="outline"><Database />已接入 {dashboardData.loadedDatasetCount} / {dashboardData.expectedDatasetCount} 份榜单</Badge><span>页面生成时间 {generatedAtLabel(dashboardData.generatedAt)}</span></div></header>
        {activePage !== "guide" && FilterBar()}
        {activePage !== "guide" && RankingAvailabilityWarning()}
        {PageHeading()}
        {activePage !== "guide" && DatasetBanner()}
        {renderPage()}
        <footer><span>数据来源：SellerSprite导出文件 · 展示范围按竞品月销售额排名定义</span><span>汇率：{dashboardData.exchangeRates.source} · {dashboardData.exchangeRates.date}</span></footer>
      </main>
      <Sheet open={Boolean(selectedProduct)} onOpenChange={(open) => { if (!open) setSelectedProduct(null); }}><SheetContent side="right" className="product-sheet"><SheetHeader><SheetTitle>商品完整字段</SheetTitle><SheetDescription>原始Excel字段仅在内部详情中展示，不占用总览页面。</SheetDescription></SheetHeader>{selectedProduct && <div className="sheet-body"><div className="sheet-product">{selectedProduct.imageUrl ? <img src={selectedProduct.imageUrl} alt="" /> : <span className="image-placeholder"><PackageSearch /></span>}<div><Badge variant="outline">竞品排名 #{productRank(selectedProduct) ?? "—"}</Badge><h3>{selectedProduct.shortTitle || selectedProduct.title}</h3><p>{selectedProduct.asin} · {selectedProduct.brand || "Unknown"}</p><p className="original-title">{selectedProduct.title}</p>{selectedProduct.productUrl && <a href={selectedProduct.productUrl} target="_blank" rel="noreferrer">打开Amazon商品页 <ExternalLink /></a>}</div></div><dl className="raw-fields">{Object.entries(selectedProduct.raw).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{Array.isArray(value) ? value.join(" · ") : typeof value === "object" && value !== null ? JSON.stringify(value, null, 2) : String(value ?? "")}</dd></div>)}</dl></div>}</SheetContent></Sheet>
    </div>
  );
}
