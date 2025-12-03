export type ViewerStyle = {
  [key: string]: string | number;
};

export interface BaseViewerProps {
  content: string;
  style?: ViewerStyle;
}
