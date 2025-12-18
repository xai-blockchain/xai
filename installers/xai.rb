# XAI Blockchain - Homebrew Formula
# ============================================================================
# Installation:
#   brew install xai-blockchain/tap/xai
#   brew tap xai-blockchain/tap
#   brew install xai
# ============================================================================

class Xai < Formula
  include Language::Python::Virtualenv

  desc "AI-Enhanced Blockchain Platform with PoW consensus and smart contracts"
  homepage "https://xai-blockchain.io"
  url "https://files.pythonhosted.org/packages/source/x/xai-blockchain/xai-blockchain-0.2.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000" # Update with actual SHA256
  license "MIT"

  # Runtime dependencies
  depends_on "python@3.12"
  depends_on "libsecp256k1"
  depends_on "gmp"
  depends_on "openssl@3"

  # Python package dependencies
  resource "flask" do
    url "https://files.pythonhosted.org/packages/source/f/flask/flask-3.0.0.tar.gz"
    sha256 "FLASK_SHA256" # Update with actual SHA256
  end

  resource "cryptography" do
    url "https://files.pythonhosted.org/packages/source/c/cryptography/cryptography-41.0.0.tar.gz"
    sha256 "CRYPTOGRAPHY_SHA256" # Update with actual SHA256
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/source/r/requests/requests-2.31.0.tar.gz"
    sha256 "REQUESTS_SHA256" # Update with actual SHA256
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/p/pyyaml/pyyaml-6.0.1.tar.gz"
    sha256 "PYYAML_SHA256" # Update with actual SHA256
  end

  resource "prometheus-client" do
    url "https://files.pythonhosted.org/packages/source/p/prometheus-client/prometheus_client-0.19.0.tar.gz"
    sha256 "PROMETHEUS_SHA256" # Update with actual SHA256
  end

  resource "secp256k1" do
    url "https://files.pythonhosted.org/packages/source/s/secp256k1/secp256k1-0.14.0.tar.gz"
    sha256 "SECP256K1_SHA256" # Update with actual SHA256
  end

  resource "websockets" do
    url "https://files.pythonhosted.org/packages/source/w/websockets/websockets-12.0.tar.gz"
    sha256 "WEBSOCKETS_SHA256" # Update with actual SHA256
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.0.tar.gz"
    sha256 "CLICK_SHA256" # Update with actual SHA256
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "RICH_SHA256" # Update with actual SHA256
  end

  def install
    # Set up virtual environment
    virtualenv_install_with_resources

    # Create data directory structure
    (var/"xai").mkpath
    (var/"xai/blockchain").mkpath
    (var/"xai/wallets").mkpath
    (var/"xai/state").mkpath
    (var/"log/xai").mkpath

    # Install default configuration
    (etc/"xai").mkpath
    (etc/"xai").install "config/genesis.json" if File.exist? "config/genesis.json"

    # Create wrapper scripts
    (bin/"xai-daemon").write <<~EOS
      #!/bin/bash
      export XAI_DATA_DIR="#{var}/xai"
      export XAI_CONFIG_DIR="#{etc}/xai"
      export XAI_LOG_DIR="#{var}/log/xai"
      exec "#{libexec}/bin/xai-node" "$@"
    EOS

    chmod 0755, bin/"xai-daemon"
  end

  def post_install
    # Create default configuration if it doesn't exist
    unless (etc/"xai/node.yaml").exist?
      (etc/"xai/node.yaml").write <<~EOS
        # XAI Node Configuration
        network:
          name: testnet
          port: 18545
          rpc_port: 18546

        data:
          dir: #{var}/xai/blockchain
          wallets_dir: #{var}/xai/wallets
          state_dir: #{var}/xai/state

        logging:
          level: INFO
          dir: #{var}/log/xai

        node:
          enable_mining: false
          max_peers: 50
          checkpoint_sync: true
      EOS
    end

    # Download genesis file if not present
    unless (etc/"xai/genesis.json").exist?
      system "curl", "-fsSL",
             "https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis.json",
             "-o", etc/"xai/genesis.json"
    end
  end

  service do
    run [opt_bin/"xai-daemon", "--network", "testnet"]
    working_dir var/"xai"
    keep_alive true
    log_path var/"log/xai/node.log"
    error_log_path var/"log/xai/error.log"
    environment_variables XAI_DATA_DIR: var/"xai",
                          XAI_CONFIG_DIR: etc/"xai",
                          XAI_LOG_DIR: var/"log/xai"
  end

  test do
    # Test that commands are available
    assert_match "XAI Blockchain", shell_output("#{bin}/xai --version")
    assert_match version.to_s, shell_output("#{bin}/xai --version")

    # Test wallet generation
    system bin/"xai-wallet", "generate-address", "--test"

    # Test configuration
    assert_predicate etc/"xai/node.yaml", :exist?
    assert_predicate var/"xai", :directory?
  end
end
