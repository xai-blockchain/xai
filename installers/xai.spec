%global pypi_name xai-blockchain
%global pypi_version 0.2.0

Name:           %{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        AI-Enhanced Blockchain Platform

License:        Apache-2.0
URL:            https://xai-blockchain.io
Source0:        https://files.pythonhosted.org/packages/source/x/%{pypi_name}/%{pypi_name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  openssl-devel
BuildRequires:  libffi-devel
BuildRequires:  libsecp256k1-devel
BuildRequires:  gmp-devel
BuildRequires:  pkgconfig
BuildRequires:  systemd-rpm-macros

Requires:       python3 >= 3.10
Requires:       python3-flask >= 3.0.0
Requires:       python3-cryptography >= 41.0.0
Requires:       python3-requests >= 2.31.0
Requires:       python3-pyyaml >= 6.0
Requires:       python3-prometheus_client >= 0.19.0
Requires:       python3-psutil >= 5.9.0
Requires:       python3-websockets >= 12.0
Requires:       python3-click >= 8.1.0

Requires(pre):  shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
XAI is a Python-based proof-of-work blockchain implementation with a UTXO
transaction model, REST API, and wallet CLI.

%package devel
Summary:        Development tools for XAI Blockchain
Requires:       %{name} = %{version}-%{release}
Requires:       python3-pytest >= 8.0.0
Requires:       python3-pytest-cov >= 4.1.0
Requires:       python3-black >= 24.0.0
Requires:       python3-pylint >= 3.0.0
Requires:       python3-mypy >= 1.8.0

%description devel
This package contains development tools and dependencies for building
and testing XAI blockchain applications.

%package doc
Summary:        Documentation for XAI Blockchain
BuildArch:      noarch

%description doc
This package contains documentation for the XAI blockchain implementation.

%prep
%autosetup -n %{pypi_name}-%{version}

%build
%py3_build

%install
%py3_install

# Create directory structure
install -d %{buildroot}%{_sharedstatedir}/xai
install -d %{buildroot}%{_sharedstatedir}/xai/blockchain
install -d %{buildroot}%{_sharedstatedir}/xai/wallets
install -d %{buildroot}%{_sharedstatedir}/xai/state
install -d %{buildroot}%{_localstatedir}/log/xai
install -d %{buildroot}%{_sysconfdir}/xai

# Install configuration files
install -m 644 config/genesis.json %{buildroot}%{_sysconfdir}/xai/ || true

# Install systemd service
install -d %{buildroot}%{_unitdir}
cat > %{buildroot}%{_unitdir}/xai-node.service <<'EOF'
[Unit]
Description=XAI Blockchain Node
Documentation=https://docs.xai-blockchain.io
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=xai
Group=xai

Environment="XAI_DATA_DIR=/var/lib/xai"
Environment="XAI_CONFIG_DIR=/etc/xai"
Environment="XAI_LOG_DIR=/var/log/xai"
Environment="XAI_NETWORK=testnet"
Environment="PYTHONUNBUFFERED=1"

ExecStart=/usr/bin/xai-node --network testnet
ExecReload=/bin/kill -HUP $MAINPID

Restart=on-failure
RestartSec=10s
TimeoutStopSec=30s

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/xai /var/log/xai

LimitNOFILE=65536
MemoryMax=4G

StandardOutput=journal
StandardError=journal
SyslogIdentifier=xai-node

[Install]
WantedBy=multi-user.target
EOF

%pre
# Create xai user and group
getent group xai >/dev/null || groupadd -r xai
getent passwd xai >/dev/null || \
    useradd -r -g xai -d %{_sharedstatedir}/xai -s /sbin/nologin \
    -c "XAI Blockchain Node" xai
exit 0

%post
# Set ownership and permissions
chown -R xai:xai %{_sharedstatedir}/xai
chown -R xai:xai %{_localstatedir}/log/xai
chown -R xai:xai %{_sysconfdir}/xai

chmod 750 %{_sharedstatedir}/xai
chmod 750 %{_localstatedir}/log/xai
chmod 755 %{_sysconfdir}/xai

# Create default configuration if it doesn't exist
if [ ! -f %{_sysconfdir}/xai/node.yaml ]; then
    cat > %{_sysconfdir}/xai/node.yaml <<'YAML'
# XAI Node Configuration

network:
  name: testnet
  port: 18545
  rpc_port: 18546

data:
  dir: /var/lib/xai/blockchain
  wallets_dir: /var/lib/xai/wallets
  state_dir: /var/lib/xai/state

logging:
  level: INFO
  dir: /var/log/xai

node:
  enable_mining: false
  max_peers: 50
  checkpoint_sync: true
YAML
    chown xai:xai %{_sysconfdir}/xai/node.yaml
    chmod 644 %{_sysconfdir}/xai/node.yaml
fi

%systemd_post xai-node.service

echo ""
echo "XAI Blockchain installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Start the node: sudo systemctl start xai-node"
echo "  2. Enable on boot: sudo systemctl enable xai-node"
echo "  3. Check status: sudo systemctl status xai-node"
echo "  4. View logs: sudo journalctl -u xai-node -f"
echo ""
echo "Configuration: /etc/xai/node.yaml"
echo "Data directory: /var/lib/xai"
echo "Logs: /var/log/xai"
echo ""

%preun
%systemd_preun xai-node.service

%postun
%systemd_postun_with_restart xai-node.service

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{python3_sitelib}/xai/
%{python3_sitelib}/%{pypi_name}-%{version}-py%{python3_version}.egg-info/
%{_bindir}/xai
%{_bindir}/xai-node
%{_bindir}/xai-wallet
%{_unitdir}/xai-node.service
%dir %attr(0750,xai,xai) %{_sharedstatedir}/xai
%dir %attr(0750,xai,xai) %{_sharedstatedir}/xai/blockchain
%dir %attr(0750,xai,xai) %{_sharedstatedir}/xai/wallets
%dir %attr(0750,xai,xai) %{_sharedstatedir}/xai/state
%dir %attr(0750,xai,xai) %{_localstatedir}/log/xai
%dir %attr(0755,xai,xai) %{_sysconfdir}/xai
%config(noreplace) %attr(0644,xai,xai) %{_sysconfdir}/xai/*.json
%config(noreplace) %attr(0644,xai,xai) %{_sysconfdir}/xai/*.yaml

%files devel
# Development files would go here

%files doc
%doc docs/*

%changelog
* Wed Dec 18 2024 XAI Team <dev@xai-blockchain.io> - 0.2.0-1
- Initial RPM release
- Added systemd service integration
- Added proper user/group creation
- Security hardening in systemd service
