import React from 'react';
import { ChangeEventHandler } from 'react';
import SearchIcon from '@/assets/icons/searchIcon.svg';
import AssetModules from '@/shared/AssetModules';
import { entity_state } from '@/types/enums';

interface ISearchInputProps {
  data: Record<string, any>[];
  inputValue: string;
  selectedValue?: Record<string, any> | null;
  className?: string;
  isOpen: boolean;
  onChange?: ChangeEventHandler<HTMLInputElement>;
  onSelect?: (item: Record<string, any>) => void;
  onClear: () => void;
  hasIcon?: boolean;
  hasClearIcon?: boolean;
  placeholder?: string;
  isSearchDataFetching?: boolean;
  inputDebouncedValue?: string;
}

export default function SearchInput({
  data,
  inputValue,
  selectedValue,
  onChange,
  onSelect,
  onClear,
  isOpen,
  className,
  inputDebouncedValue,
  hasClearIcon = true,
  isSearchDataFetching,
  placeholder = '',
}: ISearchInputProps) {
  const showClearIcon = !!inputValue.trim().length || selectedValue;

  return (
    <div
      className={`${className} fmtm-flex fmtm-group fmtm-relative fmtm-h-9 fmtm-w-[350px] fmtm-items-center fmtm-justify-between fmtm-rounded-lg fmtm-border-2 fmtm-border-grey-300 fmtm-bg-white hover:fmtm-border-primary-400`}
    >
      <div className="fmtm-flex fmtm-w-full fmtm-items-center">
        <img src={SearchIcon} alt="Search Icon" className="fmtm-h-[1.15rem] fmtm-w-[1.15rem] fmtm-mx-2" />
        <input
          value={inputValue}
          onChange={onChange}
          placeholder={inputValue || placeholder}
          className="fmtm-w-full fmtm-outline-none placeholder:fmtm-text-sm"
        />
      </div>
      {showClearIcon && hasClearIcon && <AssetModules.CloseIcon />}
      {isOpen && (
        <ul className="fmtm-scrollbar fmtm-absolute fmtm-top-10 fmtm-max-h-[20.5rem] fmtm-w-full fmtm-animate-flip-down fmtm-overflow-y-auto fmtm-bg-white">
          {data?.length ? (
            data?.map((item: Record<string, any>) => (
              <li
                key={item.id}
                className="fmtm-cursor-pointer fmtm-border-b-[0.5px] fmtm-border-grey-300 fmtm-px-4 fmtm-py-3 focus:fmtm-bg-primary-50"
                role="presentation"
                onKeyDown={() => {}}
                onClick={() => {
                  onSelect?.(item);
                }}
              >
                <div className="fmtm-flex fmtm-flex-col fmtm-gap-1">
                  <div className="fmtm-flex fmtm-flex-col">
                    <p className="fmtm-text-xs fmtm-font-bold fmtm-text-grey-800">{item?.osm_id}</p>
                    <p className="fmtm-text-xs fmtm-font-bold fmtm-leading-4 fmtm-text-primary-400">{item?.task_id}</p>
                  </div>
                  <div className="fmtm-flex fmtm-gap-1 fmtm-justify-between fmtm-text-xs">
                    <p className="fmtm-font-normal fmtm-text-grey-800">{entity_state[item.status]}</p>
                  </div>
                </div>
              </li>
            ))
          ) : isSearchDataFetching ? (
            <div className="fmtm-flex fmtm-flex-col fmtm-gap-2 fmtm-p-1">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index}>loading...</div>
              ))}
            </div>
          ) : (
            inputDebouncedValue !== '' && (
              <div className="fmtm-flex fmtm-flex-col fmtm-px-4 fmtm-py-3 fmtm-text-sm">No data found</div>
            )
          )}
        </ul>
      )}
    </div>
  );
}
