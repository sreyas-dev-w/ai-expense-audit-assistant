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