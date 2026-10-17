cask "tuttle" do
  version "5.0.0"
  sha256 "a9d33553296c6e2f3719c266c0b07ddab96359931caa806b9c75a77fe5095990"

  url "https://github.com/tuttle-dev/tuttle/releases/download/v#{version}/Tuttle-#{version}-macOS-arm64.dmg",
      verified: "github.com/tuttle-dev/tuttle/"
  name "Tuttle"
  desc "Painless business planning for freelancers"
  homepage "https://github.com/tuttle-dev/tuttle"

  livecheck do
    url :url
    strategy :github_latest
  end

  auto_updates true
  depends_on macos: ">= :ventura"

  app "Tuttle.app"

  zap trash: [
    "~/.tuttle",
    "~/Library/Application Support/dev.tuttle.app",
    "~/Library/Caches/dev.tuttle.app",
    "~/Library/Caches/dev.tuttle.app.ShipIt",
    "~/Library/Preferences/dev.tuttle.app.plist",
  ]
end
