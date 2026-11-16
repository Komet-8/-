import DeviceActivity

/// 每天零点由系统唤起：新的一天开始，重新上锁。App 没打开也会执行。
class Monitor: DeviceActivityMonitor {
    override func intervalDidStart(for activity: DeviceActivityName) {
        super.intervalDidStart(for: activity)
        Shield.sync()
    }

    override func intervalDidEnd(for activity: DeviceActivityName) {
        super.intervalDidEnd(for: activity)
        Shield.sync()
    }
}
