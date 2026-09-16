import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  radius: number;
  baseAlpha: number;
  twinkleSpeed: number;
  phase: number;
  colour: string;
}

/**
 * Real stellar colours, from hot blue-white O/B stars through the Sun's yellow-white to
 * cool red M dwarfs. Weighted towards the cooler end because that is what the sky actually
 * looks like — red dwarfs vastly outnumber blue giants.
 */
const STAR_COLOURS = [
  { colour: "#a8c8ff", weight: 3 }, // O/B — hot blue
  { colour: "#cfe0ff", weight: 6 }, // A   — blue-white
  { colour: "#f4f2ef", weight: 12 }, // F  — white
  { colour: "#fff4e8", weight: 18 }, // G  — Sun-like
  { colour: "#ffd9a8", weight: 22 }, // K  — orange
  { colour: "#ffb37a", weight: 14 }, // M  — red dwarf
];

function pickColour(random: () => number): string {
  const total = STAR_COLOURS.reduce((sum, s) => sum + s.weight, 0);
  let target = random() * total;
  for (const star of STAR_COLOURS) {
    target -= star.weight;
    if (target <= 0) return star.colour;
  }
  return "#ffffff";
}

/**
 * Animated starfield backdrop.
 *
 * Drawn on a canvas rather than with DOM elements: a few hundred animated nodes would
 * thrash layout, whereas a canvas is one composited layer. Respects
 * prefers-reduced-motion by rendering a single static frame.
 */
export function Starfield({ density = 0.00018 }: { density?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let stars: Star[] = [];
    let frame = 0;
    let width = 0;
    let height = 0;

    const build = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);

      let seed = 20240101;
      const random = () => {
        seed = (seed * 1664525 + 1013904223) % 4294967296;
        return seed / 4294967296;
      };

      const count = Math.floor(width * height * density);
      stars = Array.from({ length: count }, () => ({
        x: random() * width,
        y: random() * height,
        radius: 0.35 + random() * 1.25,
        baseAlpha: 0.25 + random() * 0.6,
        twinkleSpeed: 0.004 + random() * 0.012,
        phase: random() * Math.PI * 2,
        colour: pickColour(random),
      }));
    };

    const draw = () => {
      context.clearRect(0, 0, width, height);
      for (const star of stars) {
        const twinkle = reduceMotion
          ? 1
          : 0.65 + 0.35 * Math.sin(frame * star.twinkleSpeed + star.phase);
        context.globalAlpha = star.baseAlpha * twinkle;
        context.fillStyle = star.colour;
        context.beginPath();
        context.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        context.fill();

        // A soft halo on the brightest stars reads as diffraction without costing much.
        if (star.radius > 1.25) {
          context.globalAlpha = star.baseAlpha * twinkle * 0.12;
          context.beginPath();
          context.arc(star.x, star.y, star.radius * 3.5, 0, Math.PI * 2);
          context.fill();
        }
      }
      context.globalAlpha = 1;
    };

    let animation = 0;
    const loop = () => {
      frame += 1;
      draw();
      animation = requestAnimationFrame(loop);
    };

    build();
    if (reduceMotion) {
      draw();
    } else {
      loop();
    }

    const onResize = () => {
      build();
      draw();
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(animation);
    };
  }, [density]);

  return (
    <div className="starfield" aria-hidden="true">
      <canvas ref={canvasRef} />
      <div className="starfield__nebula starfield__nebula--one" />
      <div className="starfield__nebula starfield__nebula--two" />
      <div className="starfield__vignette" />
    </div>
  );
}
