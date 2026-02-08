import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function StatsScreen({ weeklyStats, loading }) {
    if (loading) {
        return _jsx("section", { className: "panel", children: "Loading weekly stats..." });
    }
    const entries = Object.entries(weeklyStats);
    if (entries.length === 0) {
        return _jsx("section", { className: "panel", children: "No users configured." });
    }
    return (_jsx("section", { className: "stats-grid", children: entries.map(([userName, days]) => {
            const totalMinutes = days.reduce((sum, day) => sum + day.minutes, 0);
            const metTargetDays = days.filter((day) => day.met_target).length;
            return (_jsxs("article", { className: "panel", children: [_jsx("h2", { children: userName }), _jsxs("p", { children: [Math.round(totalMinutes), " min this week, ", metTargetDays, "/7 days on target"] }), _jsx("div", { className: "bars", "aria-label": `${userName} weekly chart`, children: days.map((day) => (_jsxs("div", { className: "bar-wrap", children: [_jsx("div", { className: "bar", style: { height: `${Math.max(8, day.percentage)}%` }, title: `${day.day_name}: ${day.minutes} minutes` }), _jsx("span", { children: day.day_name })] }, day.date))) })] }, userName));
        }) }));
}
