
import { useMemo } from "react";
import { Check, Copy } from "lucide-react";
import { useState } from "react";
import Badge from "./Badge.jsx";

function InlineMarkdown({ text }) {
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g);

  return tokens.map((token, index) => {
    if (!token) return null;

    if (/^`[^`]+`$/.test(token)) {
      return <code className="md-inline-code" key={index}>{token.slice(1, -1)}</code>;
    }

    if (/^\*\*[^*]+\*\*$/.test(token) || /^__[^_]+__$/.test(token)) {
      return <strong key={index}>{token.slice(2, -2)}</strong>;
    }

    if (/^\*[^*]+\*$/.test(token) || /^_[^_]+_$/.test(token)) {
      return <em key={index}>{token.slice(1, -1)}</em>;
    }

    const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      return (
        <a key={index} href={link[2]} target="_blank" rel="noreferrer" className="md-link">
          {link[1]}
        </a>
      );
    }

    return <span key={index}>{token}</span>;
  });
}

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      // Clipboard may be unavailable in some browsers.
    }
  }

  return (
    <div className="md-code-block">
      <div className="md-code-header">
        <span>{language || "code"}</span>
        <button onClick={copyCode} type="button" className="md-copy-btn">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre><code>{code}</code></pre>
    </div>
  );
}

function MarkdownContent({ content }) {
  const blocks = useMemo(() => {
    const normalized = String(content ?? "").replace(/\r\n/g, "\n");
    const lines = normalized.split("\n");
    const output = [];
    let paragraph = [];
    let list = [];
    let listType = null;
    let code = [];
    let codeLanguage = "";
    let inCode = false;

    const flushParagraph = () => {
      if (!paragraph.length) return;
      output.push(
        <p className="md-paragraph" key={`p-${output.length}`}>
          {paragraph.map((line, i) => (
            <span key={i}>
              {i > 0 && <br />}
              <InlineMarkdown text={line} />
            </span>
          ))}
        </p>
      );
      paragraph = [];
    };

    const flushList = () => {
      if (!list.length) return;
      const Tag = listType === "ordered" ? "ol" : "ul";
      output.push(
        <Tag className="md-list" key={`l-${output.length}`}>
          {list.map((item, i) => (
            <li key={i}><InlineMarkdown text={item} /></li>
          ))}
        </Tag>
      );
      list = [];
      listType = null;
    };

    const flushCode = () => {
      if (!inCode) return;
      output.push(
        <CodeBlock
          key={`c-${output.length}`}
          code={code.join("\n")}
          language={codeLanguage}
        />
      );
      code = [];
      codeLanguage = "";
      inCode = false;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.trim().startsWith("```")) {
        if (inCode) {
          flushCode();
        } else {
          flushParagraph();
          flushList();
          inCode = true;
          codeLanguage = line.trim().slice(3).trim();
        }
        continue;
      }

      if (inCode) {
        code.push(line);
        continue;
      }

      if (!line.trim()) {
        flushParagraph();
        flushList();
        continue;
      }

      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        flushList();
        const Tag = `h${heading[1].length}`;
        output.push(
          <Tag className="md-heading" key={`h-${output.length}`}>
            <InlineMarkdown text={heading[2]} />
          </Tag>
        );
        continue;
      }

      const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);

      if (unordered || ordered) {
        flushParagraph();
        const nextType = unordered ? "unordered" : "ordered";
        if (listType && listType !== nextType) flushList();
        listType = nextType;
        list.push((unordered || ordered)[1]);
        continue;
      }

      // Simple blockquote support.
      if (/^\s*>\s?/.test(line)) {
        flushParagraph();
        flushList();
        output.push(
          <blockquote className="md-quote" key={`q-${output.length}`}>
            <InlineMarkdown text={line.replace(/^\s*>\s?/, "")} />
          </blockquote>
        );
        continue;
      }

      // Basic markdown table support.
      if (
        line.includes("|") &&
        i + 1 < lines.length &&
        /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(lines[i + 1])
      ) {
        flushParagraph();
        flushList();

        const parseCells = (row) =>
          row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

        const headers = parseCells(line);
        const rows = [];
        i += 2;
        while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
          rows.push(parseCells(lines[i]));
          i++;
        }
        i--;

        output.push(
          <div className="md-table-wrap" key={`t-${output.length}`}>
            <table className="md-table">
              <thead>
                <tr>{headers.map((h, j) => <th key={j}><InlineMarkdown text={h} /></th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row, r) => (
                  <tr key={r}>
                    {headers.map((_, c) => <td key={c}><InlineMarkdown text={row[c] || ""} /></td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }

      paragraph.push(line);
    }

    flushParagraph();
    flushList();
    flushCode();

    return output;
  }, [content]);

  return <div className="markdown-content">{blocks}</div>;
}

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="message-row message-row--user">
        <div className="user-bubble">{content}</div>
      </div>
    );
  }

  return (
    <div className="message-row message-row--assistant">
      <Badge size={30} />
      <div className="assistant-response">
        <MarkdownContent content={content} />
      </div>
    </div>
  );
}
