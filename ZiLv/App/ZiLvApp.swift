import SwiftUI

@main
struct ZiLvApp: App {
    @StateObject private var model = Model()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .onChange(of: scenePhase) { phase in
                    if phase == .active { model.refresh() }
                }
        }
    }
}
