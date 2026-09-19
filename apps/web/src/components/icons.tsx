import * as React from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import type { HugeiconsIconProps, IconSvgElement } from "@hugeicons/react"
import {
  ArrowLeftIcon as ArrowLeftIconPath,
  BriefcaseIcon as BriefcaseIconPath,
  BuildingIcon as BuildingIconPath,
  Cancel01Icon as CancelXIconPath,
  CancelCircleIcon as CircleXIconPath,
  CheckIcon as CheckIconPath,
  CheckmarkCircleIcon as CircleCheckIconPath,
  ChevronDownIcon as ChevronDownIconPath,
  ChevronRightIcon as ChevronRightIconPath,
  ChevronUpIcon as ChevronUpIconPath,
  CirclePlusIcon as PlusCircleIconPath,
  ClipboardCheckIcon as ClipboardCheckIconPath,
  Copy01Icon as CopyIconPath,
  Delete02Icon as Trash2IconPath,
  FileIcon as FileIconPath,
  FileQuestionMarkIcon as FileQuestionIconPath,
  FileSearchIcon as FileSearchIconPath,
  FileTextIcon as FileTextIconPath,
  ImageOffIcon as ImageOffIconPath,
  InfoIcon as InfoIconPath,
  LoaderIcon as Loader2IconPath,
  LogOutIcon as LogOutIconPath,
  Moon01Icon as MoonIconPath,
  MoreHorizontalIcon as MoreHorizontalIconPath,
  OctagonAlertIcon as OctagonAlertIconPath,
  OctagonXIcon as OctagonXIconPath,
  PanelLeftIcon as PanelLeftIconPath,
  PlusSignIcon as PlusIconPath,
  QuoteUpIcon as QuoteIconPath,
  RotateCcwIcon as RotateCcwIconPath,
  ScaleIcon as ScaleIconPath,
  Search01Icon as SearchIconPath,
  ShieldCheckIcon as ShieldCheckIconPath,
  Sun01Icon as SunIconPath,
  TriangleAlertIcon as TriangleAlertIconPath,
  Upload01Icon as UploadIconPath,
  UserIcon as UserIconPath,
} from "@hugeicons/core-free-icons"
import {
  BankIcon as BankIconPath,
  Calendar01Icon as CalendarIconPath,
  CheckmarkBadge01Icon as CheckmarkBadgeIconPath,
  Clock01Icon as ClockIconPath,
  DatabaseIcon as DatabaseIconPath,
  DnaIcon as DnaIconPath,
  DocumentValidationIcon as DocumentValidationIconPath,
  EncryptIcon as EncryptIconPath,
  FileValidationIcon as FileValidationIconPath,
  FingerPrintIcon as FingerprintIconPath,
  FlowIcon as FlowIconPath,
  FolderCheckIcon as FolderCheckIconPath,
  GavelIcon as GavelIconPath,
  LockKeyIcon as LockKeyIconPath,
  ReceiptIcon as ReceiptIconPath,
  ReceiptIndianRupeeIcon as ReceiptIndianRupeeIconPath,
  ReceiptTextIcon as ReceiptTextIconPath,
  SafeIcon as SafeIconPath,
  UserGroupIcon as UserGroupIconPath,
  Wallet01Icon as WalletIconPath,
  WorkflowIcon as WorkflowIconPath,
  ZapIcon as ZapIconPath,
} from "@hugeicons/core-free-icons"

type IconProps = Omit<HugeiconsIconProps, "icon">

function createIcon(icon: IconSvgElement, name: string) {
  function Icon(props: IconProps) {
    return <HugeiconsIcon icon={icon} {...props} />
  }
  Icon.displayName = name
  return Icon
}

export const ArrowLeftIcon = createIcon(ArrowLeftIconPath, "ArrowLeftIcon")
export const BriefcaseIcon = createIcon(BriefcaseIconPath, "BriefcaseIcon")
export const BuildingIcon = createIcon(BuildingIconPath, "BuildingIcon")
export const CheckIcon = createIcon(CheckIconPath, "CheckIcon")
export const ChevronDownIcon = createIcon(ChevronDownIconPath, "ChevronDownIcon")
export const ChevronRightIcon = createIcon(ChevronRightIconPath, "ChevronRightIcon")
export const ChevronUpIcon = createIcon(ChevronUpIconPath, "ChevronUpIcon")
export const CircleCheckIcon = createIcon(CircleCheckIconPath, "CircleCheckIcon")
export const CircleXIcon = createIcon(CircleXIconPath, "CircleXIcon")
export const ClipboardCheckIcon = createIcon(ClipboardCheckIconPath, "ClipboardCheckIcon")
export const CopyIcon = createIcon(CopyIconPath, "CopyIcon")
export const FileIcon = createIcon(FileIconPath, "FileIcon")
export const FileQuestionIcon = createIcon(FileQuestionIconPath, "FileQuestionIcon")
export const FileSearchIcon = createIcon(FileSearchIconPath, "FileSearchIcon")
export const FileTextIcon = createIcon(FileTextIconPath, "FileTextIcon")
export const ImageOffIcon = createIcon(ImageOffIconPath, "ImageOffIcon")
export const InfoIcon = createIcon(InfoIconPath, "InfoIcon")
export const Loader2Icon = createIcon(Loader2IconPath, "Loader2Icon")
export const LogOutIcon = createIcon(LogOutIconPath, "LogOutIcon")
export const MoonIcon = createIcon(MoonIconPath, "MoonIcon")
export const MoreHorizontalIcon = createIcon(MoreHorizontalIconPath, "MoreHorizontalIcon")
export const OctagonAlertIcon = createIcon(OctagonAlertIconPath, "OctagonAlertIcon")
export const OctagonXIcon = createIcon(OctagonXIconPath, "OctagonXIcon")
export const PanelLeftIcon = createIcon(PanelLeftIconPath, "PanelLeftIcon")
export const PlusCircleIcon = createIcon(PlusCircleIconPath, "PlusCircleIcon")
export const PlusIcon = createIcon(PlusIconPath, "PlusIcon")
export const QuoteIcon = createIcon(QuoteIconPath, "QuoteIcon")
export const RotateCcwIcon = createIcon(RotateCcwIconPath, "RotateCcwIcon")
export const ScaleIcon = createIcon(ScaleIconPath, "ScaleIcon")
export const SearchIcon = createIcon(SearchIconPath, "SearchIcon")
export const ShieldCheckIcon = createIcon(ShieldCheckIconPath, "ShieldCheckIcon")
export const SunIcon = createIcon(SunIconPath, "SunIcon")
export const Trash2Icon = createIcon(Trash2IconPath, "Trash2Icon")
export const TriangleAlertIcon = createIcon(TriangleAlertIconPath, "TriangleAlertIcon")
export const UploadIcon = createIcon(UploadIconPath, "UploadIcon")
export const UserIcon = createIcon(UserIconPath, "UserIcon")
export const XIcon = createIcon(CancelXIconPath, "XIcon")
export const BankIcon = createIcon(BankIconPath, "BankIcon")
export const CalendarIcon = createIcon(CalendarIconPath, "CalendarIcon")
export const CheckmarkBadgeIcon = createIcon(CheckmarkBadgeIconPath, "CheckmarkBadgeIcon")
export const ClockIcon = createIcon(ClockIconPath, "ClockIcon")
export const DatabaseIcon = createIcon(DatabaseIconPath, "DatabaseIcon")
export const DnaIcon = createIcon(DnaIconPath, "DnaIcon")
export const DocumentValidationIcon = createIcon(DocumentValidationIconPath, "DocumentValidationIcon")
export const EncryptIcon = createIcon(EncryptIconPath, "EncryptIcon")
export const FileValidationIcon = createIcon(FileValidationIconPath, "FileValidationIcon")
export const FingerprintIcon = createIcon(FingerprintIconPath, "FingerprintIcon")
export const FlowIcon = createIcon(FlowIconPath, "FlowIcon")
export const FolderCheckIcon = createIcon(FolderCheckIconPath, "FolderCheckIcon")
export const GavelIcon = createIcon(GavelIconPath, "GavelIcon")
export const LockKeyIcon = createIcon(LockKeyIconPath, "LockKeyIcon")
export const ReceiptIcon = createIcon(ReceiptIconPath, "ReceiptIcon")
export const ReceiptIndianRupeeIcon = createIcon(ReceiptIndianRupeeIconPath, "ReceiptIndianRupeeIcon")
export const ReceiptTextIcon = createIcon(ReceiptTextIconPath, "ReceiptTextIcon")
export const SafeIcon = createIcon(SafeIconPath, "SafeIcon")
export const UserGroupIcon = createIcon(UserGroupIconPath, "UserGroupIcon")
export const WalletIcon = createIcon(WalletIconPath, "WalletIcon")
export const WorkflowIcon = createIcon(WorkflowIconPath, "WorkflowIcon")
export const ZapIcon = createIcon(ZapIconPath, "ZapIcon")