import { Sparkles } from 'lucide-react';
import { Button } from './ui/button';

interface DemoDataButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

const SAMPLE_MESSAGES = `[10/04/2026, 10:30:45] Rajesh Kumar: 2BHK for rent in Koregaon Park
North Main Road, near ABC Mall
1200 sqft, Price: 35000/month, Deposit: 70000
Contact: 9876543210

[10/04/2026, 11:15:20] Priya Sharma: 3BHK resale in Baner
Baner Road, Opposite XYZ Complex
1800 sqft, Price: 1.2 Cr
Call 9123456789

[11/04/2026, 09:20:15] Amit Patel: 2BHK available for rent
Location: Hinjewadi Phase 2, IT Park Road
Size: 1100 sqft
Rent: 28000/month, Deposit: 56000
Contact: 9988776655

[11/04/2026, 13:45:30] Neha Singh: Looking to sell 2BHK in Wakad
Main Street, Tower A
1300 sqft, Asking price: 85 Lakh
Call 9445566778

[11/04/2026, 15:00:00] Vikram Desai: 3BHK rental property
Viman Nagar, Airport Road, near Terminal
1600 sqft, Monthly rent 42000, Deposit 84000

[09/04/2026, 08:30:00] Sanjay Mehta: Flat for rent in Kharadi
EON IT Park vicinity, 2BHK, 1250 sqft
32000 per month, 2 months deposit
Contact: 9334455667

[09/04/2026, 14:20:00] Anita Reddy: Selling 3BHK apartment in Aundh
Aundh Road, near Metro station
2000 sqft, Price 1.8 Crore
Interested buyers call 9556677889

[08/04/2026, 16:45:00] Ramesh Kulkarni: 2BHK for rent
Pimple Saudagar, Main Road, Phase 3
1150 sqft, 26000/month + 52000 deposit
Ph: 9667788990`;

export function DemoDataButton({ onClick, disabled }: DemoDataButtonProps) {
  const handleClick = () => {
    onClick();
  };

  return (
    <Button
      variant="outline"
      onClick={handleClick}
      disabled={disabled}
      className="gap-2 border-dashed border-2 hover:border-primary hover:bg-primary/5"
    >
      <Sparkles className="w-4 h-4" />
      Load Demo Data
    </Button>
  );
}

export { SAMPLE_MESSAGES };
