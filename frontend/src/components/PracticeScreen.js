import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
export function PracticeScreen({ session, onEndSession, ending }) {
    const duration = session.duration ?? 0;
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60)
        .toString()
        .padStart(2, '0');
    return (_jsxs("section", { className: "panel", children: [_jsxs("h2", { children: [session.user, " is practicing"] }), _jsxs("p", { children: ["Duration: ", minutes, ":", seconds] }), _jsxs("p", { children: ["Notes: ", session.note_count ?? 0] }), _jsx("button", { onClick: onEndSession, disabled: ending, children: ending ? 'Ending...' : 'End Session' })] }));
}
