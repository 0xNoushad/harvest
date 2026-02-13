import { WalletAdapterNetwork } from '@solana/wallet-adapter-base';
import { ConnectionProvider, WalletProvider, useWallet } from '@solana/wallet-adapter-react';
import { WalletModalProvider, WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import {
  PhantomWalletAdapter,
  SolflareWalletAdapter,
  LedgerWalletAdapter,
} from '@solana/wallet-adapter-wallets';
import { clusterApiUrl } from '@solana/web3.js';
import { useMemo, useEffect } from 'react';

// Import wallet adapter CSS
import '@solana/wallet-adapter-react-ui/styles.css';

type WalletConnectProps = {
  network?: WalletAdapterNetwork;
  onConnect?: (publicKey: string) => void;
};

const WalletButton = ({ onConnect }: { onConnect?: (publicKey: string) => void }) => {
  const { publicKey, connected } = useWallet();

  useEffect(() => {
    if (connected && publicKey && onConnect) {
      onConnect(publicKey.toString());
    }
  }, [connected, publicKey, onConnect]);

  return (
    <WalletMultiButton className="!bg-dark !text-paper !rounded-xl !px-6 !py-3 !font-semibold hover:!scale-[1.02] active:!scale-[0.98] !transition-all !shadow-md !border-0 !text-sm !min-w-[180px]" />
  );
};

const WalletConnect = ({ network = WalletAdapterNetwork.Mainnet, onConnect }: WalletConnectProps) => {
  // Configure RPC endpoint
  const endpoint = useMemo(() => {
    if (network === WalletAdapterNetwork.Mainnet) {
      // cSpell:ignore helius
      const heliusKey = import.meta.env.PUBLIC_HELIUS_API_KEY;
      if (heliusKey) {
        return `https://rpc.helius.xyz/?api-key=${heliusKey}`;
      }
    }
    return clusterApiUrl(network);
  }, [network]);

  // Configure supported wallets
  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new SolflareWalletAdapter(),
      new LedgerWalletAdapter(),
    ],
    []
  );

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>
          <WalletButton onConnect={onConnect} />
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
};

export default WalletConnect;
