import SwiftUI
import FamilyControls

struct ContentView: View {
    @EnvironmentObject var model: Model
    @State private var newTitle = ""
    @State private var managing = false
    @State private var picking = false

    var body: some View {
        NavigationStack {
            List {
                Section { verdict.listRowInsets(EdgeInsets()).listRowBackground(Color.clear) }

                Section {
                    if model.todayGoals.isEmpty {
                        Text("还没有目标。先写下每天必须做的事。").foregroundStyle(.secondary)
                    }
                    ForEach(model.todayGoals) { goal in goalRow(goal) }
                    HStack {
                        TextField("添加每日目标，例如：背单词 50 个", text: $newTitle)
                            .onSubmit(addGoal)
                        Button("添加", action: addGoal)
                            .disabled(newTitle.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                } header: {
                    HStack {
                        Text("今天必须完成")
                        Spacer()
                        if !model.todayGoals.isEmpty {
                            Button(managing ? "完成" : "管理") { managing.toggle() }.font(.footnote)
                        }
                    }
                } footer: {
                    Text("目标每天重复。删除旧目标从明天起才生效，今天照样要完成。")
                }

                Section("没完成时锁住的 App") { lockSection }

                Section("执行记录") { record }
            }
            .navigationTitle("自律监督")
            .familyActivityPicker(isPresented: $picking, selection: $model.selection)
        }
    }

    private var verdict: some View {
        let p = model.progress
        let idle = p.total == 0
        let color: Color = idle ? .gray : (model.locked ? .red : .green)
        return VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 14) {
                Image(systemName: model.locked ? "lock.fill" : "lock.open.fill").font(.system(size: 36))
                VStack(alignment: .leading, spacing: 2) {
                    Text(idle ? "还没有目标" : (model.locked ? "锁定中，不许玩手机" : "已解锁，可以玩手机"))
                        .font(.title2.bold())
                    Text(idle ? "定好目标后开始监督" : (model.locked ? "还差 \(p.total - p.done) 项没完成" : "今天的目标全部完成"))
                        .font(.subheadline)
                }
            }
            ProgressView(value: idle ? 0 : Double(p.done), total: idle ? 1 : Double(p.total)).tint(.white)
            HStack {
                Text(idle ? "" : "已完成 \(p.done) / \(p.total)")
                Spacer()
                if model.streaks.current > 0 { Text("连续达标 \(model.streaks.current) 天") }
            }
            .font(.footnote.monospacedDigit())
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(color, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func goalRow(_ goal: Goal) -> some View {
        let done = model.isDone(goal)
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                Button { model.toggle(goal) } label: {
                    Image(systemName: done ? "checkmark.circle.fill" : "circle")
                        .font(.title2)
                        .foregroundStyle(done ? Color.green : Color.secondary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(done ? "取消完成 \(goal.title)" : "标记完成 \(goal.title)")
                Text(goal.title).strikethrough(done).foregroundStyle(done ? .secondary : .primary)
                Spacer()
                if goal.until == model.today { Text("明天起取消").font(.caption).foregroundStyle(.secondary) }
                if managing {
                    Button(goal.until == model.today ? "恢复" : "删除") { model.remove(goal) }
                        .buttonStyle(.bordered).tint(.red).font(.footnote)
                }
            }
            if done {
                TextField("写一句具体完成了什么（可选）", text: Binding(
                    get: { model.note(for: goal) },
                    set: { model.setNote($0, for: goal) }
                ))
                .font(.subheadline)
                .padding(.leading, 40)
            }
        }
    }

    @ViewBuilder private var lockSection: some View {
        if !model.authorized {
            Button("允许“屏幕使用时间”权限") { model.requestAuthorization() }
            if let error = model.authError { Text(error).font(.footnote).foregroundStyle(.red) }
            Text("需要这个权限才能在目标没完成时屏蔽 App。").font(.footnote).foregroundStyle(.secondary)
        } else {
            let count = model.selection.applicationTokens.count + model.selection.categoryTokens.count
            Button(model.hasSelection ? "已选择 \(count) 项，点这里修改" : "选择要锁住的 App") { picking = true }
                .disabled(model.locked && model.hasSelection)
            Text(model.locked && model.hasSelection
                 ? "锁定期间不能修改名单。完成今天的目标后再改。"
                 : "建议选游戏、短视频、社交这些最耽误时间的。")
                .font(.footnote).foregroundStyle(.secondary)
        }
    }

    private var record: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                stat("\(model.streaks.current)", "连续达标天数")
                Divider()
                stat("\(model.streaks.best)", "最长连续")
            }
            HStack(spacing: 4) {
                ForEach(model.last14) { cell in
                    VStack(spacing: 4) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(color(for: cell))
                            .aspectRatio(1, contentMode: .fit)
                        Text("\(cell.dayNumber)").font(.system(size: 9).monospacedDigit()).foregroundStyle(.secondary)
                    }
                }
            }
            Text("绿色：全部完成　黄色：完成一部分　红色：一项没做").font(.caption).foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private func stat(_ value: String, _ label: String) -> some View {
        VStack(spacing: 2) {
            Text(value).font(.system(size: 32, weight: .bold, design: .rounded).monospacedDigit())
            Text(label).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func color(for cell: Model.DayCell) -> Color {
        if cell.total == 0 { return Color.gray.opacity(0.25) }
        if cell.done == cell.total { return .green }
        if cell.done > 0 { return .yellow }
        return cell.id == model.today ? Color.gray.opacity(0.25) : .red
    }

    private func addGoal() {
        model.add(newTitle)
        newTitle = ""
    }
}
