import { motion } from 'framer-motion';

export default function StreakCalendar({ streak = 0, history = [] }) {
  // Generate last 30 days
  const days = Array.from({ length: 30 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i)); // Go back from today
    return date;
  });

  // Check if a date is active
  const isActive = (date, index) => {
    // Priority 1: Real History
    if (history && history.length > 0) {
      const dateStr = date.toISOString().split('T')[0];
      return history.some(h => {
        const hDate = new Date(h.date).toISOString().split('T')[0];
        return hDate === dateStr && h.activityCount > 0;
      });
    }
    
    // Priority 2: Fallback to simple streak count (Visual Mock)
    // If we have a 5 day streak, the last 5 days are active
    return index >= 30 - streak;
  };

  return (
    <div className="bg-hyper-card p-6 rounded-2xl border border-gray-800">
      <h3 className="text-xl font-bold mb-4 text-gray-300">Neural Sync History</h3>
      <div className="grid grid-cols-7 gap-2">
        {days.map((date, i) => {
          const active = isActive(date, i);
          return (
            <motion.div
              key={i}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.02 }}
              className={`
                aspect-square rounded-md flex items-center justify-center text-xs font-mono relative group cursor-default
                ${active 
                  ? 'bg-hyper-accent text-black shadow-[0_0_10px_rgba(0,255,255,0.5)]' 
                  : 'bg-gray-800/50 text-gray-600'}
              `}
            >
              {date.getDate()}
              
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block bg-black text-white text-xs p-1 rounded border border-gray-700 whitespace-nowrap z-10 pointer-events-none">
                {date.toLocaleDateString()}
                {active && <span className="block text-hyper-accent">Active Session</span>}
              </div>
            </motion.div>
          );
        })}
      </div>
      <div className="mt-4 text-xs text-gray-500 text-center">
        Last 30 Days • {streak} Day Streak Active
      </div>
    </div>
  );
}
