'use client';
import { motion } from 'framer-motion';

export default function PaperReader({ content, highlights }) {
  const lines = content.split('\n');
  return (
    <div className="prose max-w-none p-4">
      {lines.map((line, i) => (
        <motion.p
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={highlights.includes(i) ? 'bg-yellow-200 p-2 rounded' : ''}
        >
          {line}
        </motion.p>
      ))}
    </div>
  );
}