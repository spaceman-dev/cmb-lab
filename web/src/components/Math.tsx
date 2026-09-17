import { useEffect, useMemo, useRef } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

interface MathProps {
  tex: string;
  display?: boolean;
  className?: string;
}

/** A single KaTeX expression. */
export function Math({ tex, display = false, className }: MathProps) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(tex, {
        displayMode: display,
        throwOnError: false,
        strict: false,
        trust: false,
        output: "html",
      });
    } catch {
      return `<code>${tex}</code>`;
    }
  }, [tex, display]);

  return (
    <span
      className={className}
      // KaTeX output is generated locally from our own lesson content, never user input.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/**
 * Prose containing `$inline$` and `$$display$$` math, plus light markdown.
 *
 * Written by hand rather than pulled from a markdown library because the content is ours
 * and the surface needed is small — bold, italics, headings, lists, code, and math. That
 * also means no third-party HTML ever reaches dangerouslySetInnerHTML.
 */
export function RichText({ text, className }: { text: string; className?: string }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = container.current;
    if (!node) return;

    const escape = (s: string) =>
      s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

    const renderMath = (tex: string, display: boolean) => {
      try {
        return katex.renderToString(tex, {
          displayMode: display,
          throwOnError: false,
          strict: false,
          output: "html",
        });
      } catch {
        return `<code>${escape(tex)}</code>`;
      }
    };

    // Pull math out first so markdown substitution cannot corrupt LaTeX syntax
    // (underscores and asterisks are meaningful in both languages).
    const slots: string[] = [];
    let work = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => {
      slots.push(`<div class="math-block">${renderMath(tex.trim(), true)}</div>`);
      return `\u0000${slots.length - 1}\u0000`;
    });
    work = work.replace(/\$([^$\n]+?)\$/g, (_, tex) => {
      slots.push(renderMath(tex.trim(), false));
      return `\u0000${slots.length - 1}\u0000`;
    });

    work = escape(work);

    const blocks = work
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => {
        let out = block
          .replace(/`([^`]+)`/g, "<code>$1</code>")
          .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
          .replace(/(^|[\s(])_([^_]+)_/g, "$1<em>$2</em>");

        if (/^#{1,3}\s/.test(out)) {
          const level = out.match(/^#+/)?.[0].length ?? 1;
          return `<h${level + 2}>${out.replace(/^#+\s*/, "")}</h${level + 2}>`;
        }

        if (/^[-*]\s/m.test(out)) {
          const items = out
            .split("\n")
            .filter((line) => /^[-*]\s/.test(line.trim()))
            .map((line) => `<li>${line.trim().replace(/^[-*]\s*/, "")}</li>`)
            .join("");
          if (items) return `<ul>${items}</ul>`;
        }

        out = out.replace(/\n/g, "<br/>");
        return `<p>${out}</p>`;
      })
      .join("");

    node.innerHTML = blocks.replace(/\u0000(\d+)\u0000/g, (_, i) => slots[Number(i)] ?? "");
  }, [text]);

  return <div ref={container} className={className} />;
}

/**
 * Inline `$math$` inside a run of text, rendered as spans.
 *
 * Headings need this rather than RichText: RichText wraps its output in a div, which is
 * invalid inside an h1/h2 and makes the browser hoist it out of the heading.
 */
export function MathText({ text, className }: { text: string; className?: string }) {
  const parts = useMemo(() => text.split(/(\$[^$]+\$)/g), [text]);

  return (
    <span className={className}>
      {parts.map((part, i) =>
        part.startsWith("$") && part.endsWith("$") && part.length > 2 ? (
          <Math key={i} tex={part.slice(1, -1)} />
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
}
