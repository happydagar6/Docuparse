'use client';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';

export default function Sidebar({ query }) {
  const { data: results } = useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 5 }),
      });
      return res.json();
    },
  });

  return (
    <Card className="w-80 h-full p-4">
      <h3 className="font-bold">Related Works</h3>
      <ul>
        {results?.map((paper, index) => (
          <li key={index} className="text-sm">{paper.title} (Score: {paper.score.toFixed(2)})</li>
        ))}
      </ul>
    </Card>
  );
}