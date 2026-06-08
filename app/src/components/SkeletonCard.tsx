import { motion } from 'framer-motion';

export default function SkeletonCard({ height = 200 }: { height?: number }) {
  return (
    <div
      className="void-card"
      style={{ height, overflow: 'hidden' }}
    >
      <motion.div
        initial={{ opacity: 0.4 }}
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        style={{ height: '100%' }}
      >
        {/* Header skeleton */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
          <div
            style={{
              width: 120,
              height: 14,
              borderRadius: 6,
              background: 'linear-gradient(90deg, var(--surface) 25%, var(--elevated) 50%, var(--surface) 75%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 1.5s infinite',
            }}
          />
          <div
            style={{
              width: 80,
              height: 14,
              borderRadius: 6,
              background: 'var(--surface)',
            }}
          />
        </div>
        {/* Content lines */}
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            style={{
              width: `${60 + Math.random() * 40}%`,
              height: 10,
              borderRadius: 5,
              background: 'var(--surface)',
              marginBottom: 12,
            }}
          />
        ))}
      </motion.div>
    </div>
  );
}
