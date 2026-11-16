import Foundation
import FamilyControls
import ManagedSettings

/// App 和监控扩展共用的数据与上锁逻辑。
enum Shared {
    static let group = "group.com.komet8.zilv"
    static var defaults: UserDefaults { UserDefaults(suiteName: group) ?? .standard }
}

enum Day {
    private static let formatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
    static func key(_ date: Date = Date()) -> String { formatter.string(from: date) }
    static func date(_ key: String) -> Date? { formatter.date(from: key) }
}

struct Goal: Codable, Identifiable, Equatable {
    var id = UUID()
    var title: String
    /// 生效的第一天
    var from: String
    /// 生效的最后一天（删除旧目标时设为当天，所以当天仍然要完成）
    var until: String?
}

struct DoneMark: Codable, Equatable {
    var at: Date
    var note: String
}

struct AppState: Codable, Equatable {
    var goals: [Goal] = []
    /// 日期 -> 目标 id -> 完成记录
    var done: [String: [String: DoneMark]] = [:]

    func active(on day: String) -> [Goal] {
        goals.filter { g in
            if g.from > day { return false }
            if let until = g.until, until < day { return false }
            return true
        }
    }

    func progress(on day: String) -> (done: Int, total: Int) {
        let list = active(on: day)
        let marks = done[day] ?? [:]
        return (list.filter { marks[$0.id.uuidString] != nil }.count, list.count)
    }

    func isLocked(on day: String) -> Bool {
        let p = progress(on: day)
        return p.total > 0 && p.done < p.total
    }

    static func load() -> AppState {
        guard let data = Shared.defaults.data(forKey: "state"),
              let state = try? JSONDecoder().decode(AppState.self, from: data) else { return AppState() }
        return state
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) { Shared.defaults.set(data, forKey: "state") }
    }
}

enum Shield {
    static let store = ManagedSettingsStore()

    static func loadSelection() -> FamilyActivitySelection {
        guard let data = Shared.defaults.data(forKey: "selection"),
              let sel = try? PropertyListDecoder().decode(FamilyActivitySelection.self, from: data) else {
            return FamilyActivitySelection()
        }
        return sel
    }

    static func saveSelection(_ selection: FamilyActivitySelection) {
        if let data = try? PropertyListEncoder().encode(selection) { Shared.defaults.set(data, forKey: "selection") }
    }

    /// 今天的目标没做完就屏蔽所选 App，做完就放行。
    static func sync(state: AppState = .load(), selection: FamilyActivitySelection = loadSelection()) {
        if state.isLocked(on: Day.key()) {
            store.shield.applications = selection.applicationTokens.isEmpty ? nil : selection.applicationTokens
            store.shield.applicationCategories = selection.categoryTokens.isEmpty ? nil : .specific(selection.categoryTokens)
            store.shield.webDomains = selection.webDomainTokens.isEmpty ? nil : selection.webDomainTokens
            store.shield.webDomainCategories = selection.categoryTokens.isEmpty ? nil : .specific(selection.categoryTokens)
        } else {
            store.shield.applications = nil
            store.shield.applicationCategories = nil
            store.shield.webDomains = nil
            store.shield.webDomainCategories = nil
        }
    }
}
