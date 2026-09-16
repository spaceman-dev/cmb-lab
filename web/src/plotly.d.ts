declare module "plotly.js-dist-min" {
  export type PlotData = Record<string, unknown>;
  export type PlotLayout = Record<string, unknown>;
  export type PlotConfig = Record<string, unknown>;

  const Plotly: {
    react(
      root: HTMLElement,
      data: PlotData[],
      layout?: PlotLayout,
      config?: PlotConfig,
    ): Promise<void>;
    purge(root: HTMLElement): void;
    Plots: { resize(root: HTMLElement): void };
  };

  export default Plotly;
}
