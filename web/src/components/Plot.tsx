import { useEffect, useRef } from "react";
import Plotly, { type PlotConfig, type PlotData, type PlotLayout } from "plotly.js-dist-min";

interface PlotProps {
  data: PlotData[];
  layout?: PlotLayout;
  config?: PlotConfig;
  className?: string;
}

/**
 * Minimal imperative wrapper around Plotly.
 *
 * Plotly mutates the DOM node it owns, so React must not try to reconcile its children.
 * Rendering an empty div and driving it through Plotly.react keeps the two libraries from
 * fighting over the same subtree.
 */
export function Plot({ data, layout, config, className }: PlotProps) {
  const node = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = node.current;
    if (!element) return;
    void Plotly.react(element, data, layout, config);
  }, [data, layout, config]);

  useEffect(() => {
    const element = node.current;
    if (!element) return;

    const onResize = () => Plotly.Plots.resize(element);
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      Plotly.purge(element);
    };
  }, []);

  return <div ref={node} className={className} />;
}
