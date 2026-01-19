export type ScheduleConfig = {
    timezone: string;
    week: Array<{ day: string; start: string; end: string; note?: string }>;
    oncall?: Array<{ from: string; to: string; note?: string }>;
    holidays?: Array<{ date: string; name: string }>;
};

export const defaultSchedule: ScheduleConfig = {
    timezone: "America/New_York",
    week: [
        { day: "Monday", start: "08:00", end: "17:00" },
        { day: "Tuesday", start: "08:00", end: "17:00" },
        { day: "Wednesday", start: "08:00", end: "17:00" },
        { day: "Thursday", start: "08:00", end: "17:00" },
        { day: "Friday", start: "08:00", end: "17:00" },
    ],
    holidays: [
        { date: "2026-01-01", name: "New Year's Day" },
        { date: "2026-04-03", name: "Personal Day" },
        { date: "2026-05-25", name: "Memorial Day" },
        { date: "2026-07-03", name: "Independence Day (Observed)" },
        { date: "2026-09-07", name: "Labor Day" },
        { date: "2026-11-26", name: "Thanksgiving" },
        { date: "2026-11-27", name: "Day after Thanksgiving" },
        { date: "2026-12-24", name: "Christmas Eve" },
        { date: "2026-12-25", name: "Christmas Day" },
    ],
};
