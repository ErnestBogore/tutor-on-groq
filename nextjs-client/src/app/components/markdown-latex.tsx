import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface MarkdownLatexProps {
  content: string;
  className?: string;
}

export const MarkdownLatex: React.FC<MarkdownLatexProps> = ({ 
  content,
  className = ''
}) => {
  const components: Components = {
    h1: ({node, ...props}) => (
      <h1 className="text-3xl font-bold my-8 text-center leading-relaxed" {...props} />
    ),
    h2: ({node, ...props}) => (
      <h2 className="text-2xl font-bold my-6 text-center leading-relaxed" {...props} />
    ),
    h3: ({node, ...props}) => (
      <h3 className="text-xl font-bold my-4 text-center leading-relaxed" {...props} />
    ),
    
    p: ({node, ...props}) => (
      <p className="my-4 leading-relaxed text-center" {...props} />
    ),
    
    ul: ({node, ...props}) => (
      <ul className="list-disc pl-8 my-4 mx-auto max-w-2xl space-y-2 leading-relaxed text-left" {...props} />
    ),
    ol: ({node, ...props}) => (
      <ol className="list-decimal pl-8 my-4 mx-auto max-w-2xl space-y-2 leading-relaxed text-left" {...props} />
    ),
    
    li: ({node, ...props}) => (
      <li className="text-left" {...props} />
    ),
    
    blockquote: ({node, ...props}) => (
      <blockquote className="border-l-4 border-gray-200 pl-4 my-4 leading-relaxed" {...props} />
    ),
    a: ({node, ...props}) => (
      <a className="text-blue-600 hover:underline" {...props} />
    ),
  };

  return (
    <div className={`max-w-4xl mx-auto px-4 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownLatex;