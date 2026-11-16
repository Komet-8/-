import SwiftUI
import FamilyControls
import DeviceActivity

@MainActor
final class Model: ObservableObject {
    @Published var state: AppState { didSet { state.save(); Shield.sync(state: state, selection: selection) } }
    @Published var selection: FamilyActivitySelection {
        didSet { Shield.saveSelection(selection); Shield.sync(state: state, selection: selection) }
    }
    @Published var authorized = false
    @Published var authError: String?
    @Published var today = Day.key()

    init() {
        state = AppState.load()
        selection = Shield.loadSelection()
        refresh()
    }

    var todayGoals: [Goal] { state.active(on: today) }
    var progress: (done: Int, total: Int) { state.progress(on: today) }
    var locked: Bool { state.isLocked(on: today) }
    var hasSelection: Bool {
        !selection.applicationTokens.isEmpty || !selection.categoryTokens.isEmpty || !selection.webDomainTokens.isEmpty
    }

    /// 回到前台时调用：跨天后重新计算并上锁。
    func refresh() {
        today = Day.key()
        authorized = AuthorizationCenter.shared.authorizationStatus == .approved
        Shield.sync(state: state, selection: selection)
        if authorized { startMonitoring() }
    }

    func requestAuthorization() {
        Task {
            do {
                try await AuthorizationCenter.shared.requestAuthorization(for: .individual)
                authError = nil
            } catch {
                authError = "没有拿到“屏幕使用时间”权限，无法锁定 App。"
            }
            refresh()
        }
    }

    private func startMonitoring() {
        let schedule = DeviceActivitySchedule(
            intervalStart: DateComponents(hour: 0, minute: 0),
            intervalEnd: DateComponents(hour: 23, minute: 59),
            repeats: true
        )
        try? DeviceActivityCenter().startMonitoring(DeviceActivityName("daily"), during: schedule)
    }

    func add(_ title: String) {
        let t = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        state.goals.append(Goal(title: t, from: today))
    }

    func isDone(_ goal: Goal) -> Bool { state.done[today]?[goal.id.uuidString] != nil }

    func toggle(_ goal: Goal) {
        var marks = state.done[today] ?? [:]
        let key = goal.id.uuidString
        if marks[key] == nil { marks[key] = DoneMark(at: Date(), note: "") } else { marks[key] = nil }
        state.done[today] = marks
    }

    func note(for goal: Goal) -> String { state.done[today]?[goal.id.uuidString]?.note ?? "" }

    func setNote(_ text: String, for goal: Goal) {
        guard state.done[today]?[goal.id.uuidString] != nil else { return }
        state.done[today]?[goal.id.uuidString]?.note = text
    }

    /// 今天新加的目标可以直接删；旧目标从明天起才取消，今天仍要完成。
    func remove(_ goal: Goal) {
        guard let i = state.goals.firstIndex(where: { $0.id == goal.id }) else { return }
        if state.goals[i].until == today {
            state.goals[i].until = nil
        } else if state.goals[i].from == today {
            state.done[today]?[goal.id.uuidString] = nil
            state.goals.remove(at: i)
        } else {
            state.goals[i].until = today
        }
    }

    struct DayCell: Identifiable {
        let id: String
        let dayNumber: Int
        let done: Int
        let total: Int
    }

    var last14: [DayCell] {
        let cal = Calendar.current
        return (0..<14).reversed().compactMap { offset in
            guard let date = cal.date(byAdding: .day, value: -offset, to: Date()) else { return nil }
            let key = Day.key(date)
            let p = state.progress(on: key)
            return DayCell(id: key, dayNumber: cal.component(.day, from: date), done: p.done, total: p.total)
        }
    }

    var streaks: (current: Int, best: Int) {
        guard let first = state.goals.map(\.from).min(), var date = Day.date(first) else { return (0, 0) }
        let cal = Calendar.current
        var run = 0, best = 0
        while Day.key(date) <= today {
            let key = Day.key(date)
            let p = state.progress(on: key)
            if p.total > 0 {
                if p.done == p.total { run += 1; best = max(best, run) } else if key != today { run = 0 }
            }
            guard let next = cal.date(byAdding: .day, value: 1, to: date) else { break }
            date = next
        }
        return (run, best)
    }
}
