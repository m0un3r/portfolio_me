export interface NavigationItem {
  id: string;
  label: { en: string; ar: string };
  href: string;
  isExternal?: boolean;
}

export interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  badge?: string;
  glowColor?: string;
  accentBorder?: boolean;
}